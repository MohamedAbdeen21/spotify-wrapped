package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strconv"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/athena"
	"github.com/aws/aws-sdk-go-v2/service/athena/types"
)

const (
	plays = iota
	artists
	duration
)

type Query struct {
	Type int
	Sql  string
}

func GetQueryResults(client *athena.Client, QueryID *string) ([]types.Row, error) {

	params := &athena.GetQueryResultsInput{
		QueryExecutionId: QueryID,
	}

	data, err := client.GetQueryResults(context.TODO(), params)

	for err != nil {
		if strings.Contains(err.Error(), "FAILED") {
			log.Printf("Query execution failed: %s\n", err.Error())
			return nil, errors.New("Query Execution failed")
		}
		time.Sleep(2 * time.Second)
		data, err = client.GetQueryResults(context.TODO(), params)
	}

	return data.ResultSet.Rows, nil
}

func ExecuteQuery(client *athena.Client, query Query, result chan any) {
	cntxt := &types.QueryExecutionContext{
		Catalog:  aws.String("listening_history"),
		Database: aws.String("default"),
	}

	conf := &types.ResultConfiguration{
		OutputLocation: aws.String("s3://spotify-wrapped-spill/test/"),
	}
	params := &athena.StartQueryExecutionInput{
		QueryString:           aws.String(query.Sql),
		ResultConfiguration:   conf,
		QueryExecutionContext: cntxt,
	}

	resp, err := client.StartQueryExecution(context.TODO(), params)
	if err != nil {
		log.Fatalln(err.Error())
		close(result)
		return
	}

	queryId := resp.QueryExecutionId
	query_result, err := GetQueryResults(client, queryId)

	if err != nil {
		log.Fatalln(err.Error())
		close(result)
		return
	}

	switch query.Type {
	case 0:
		var rows []map[string]any
		for _, value := range query_result[1:] {
			data := value.Data
			duration_seconds_f, _ := strconv.ParseFloat(*data[2].VarCharValue, 64)
			duration_second := int(duration_seconds_f)
			row := map[string]any{
				"name":     data[0].VarCharValue,
				"plays":    data[1].VarCharValue,
				"duration": duration_second / 60,
				"image":    data[3].VarCharValue,
			}
			rows = append(rows, row)
		}
		result <- rows

	case 1:
		var rows []map[string]any
		for _, value := range query_result[1:] {
			data := value.Data
			duration_seconds_f, _ := strconv.ParseFloat(*data[2].VarCharValue, 64)
			duration_second := int(duration_seconds_f)
			row := map[string]any{
				"name":     data[0].VarCharValue,
				"plays":    data[1].VarCharValue,
				"duration": duration_second / 60,
			}
			rows = append(rows, row)
		}
		result <- rows

	case 2:
		for _, value := range query_result[1:] {
			duration_seconds_f, _ := strconv.ParseFloat(*value.Data[0].VarCharValue, 64)
			duration_second := int(duration_seconds_f)
			result <- duration_second / 60
		}
	}

	close(result)
}

func GetUserData(client *athena.Client, user string) map[string]any {
	result := make(map[string]any)

	// list of maps[string][string | int]
	plays_result := make(chan any)
	// int
	duration_result := make(chan any)
	// list of maps[string][string | int]
	artists_result := make(chan any)

	filter := fmt.Sprintf(`WHERE email='%s'
				AND CAST("timestamp" AS INT) < %d
				AND CAST("timestamp" AS INT) > %d`,
		user, time.Now().Unix(), time.Now().Unix()-(3600*24*7))

	plays_query := Query{
		Type: plays,
		Sql: fmt.Sprintf(`SELECT name, COUNT(*), SUM(duration_seconds) AS total_time, image
			    FROM listening_history %s
			    GROUP BY (name, image)
			    ORDER BY total_time
			    DESC LIMIT 5`, filter),
	}

	duration_query := Query{
		Type: duration,
		Sql:  fmt.Sprintf("SELECT SUM(duration_seconds) FROM listening_history %s", filter),
	}

	artists_query := Query{
		Type: artists,
		Sql: fmt.Sprintf(`SELECT artist, count(artist), sum(duration_seconds) as total
			    FROM listening_history, unnest(artists) as t(artist)
			    %s
			    GROUP BY artist
			    ORDER BY total
			    DESC LIMIT 5`, filter),
	}

	result["email"] = user

	go ExecuteQuery(client, plays_query, plays_result)
	go ExecuteQuery(client, duration_query, duration_result)
	go ExecuteQuery(client, artists_query, artists_result)

	// blocking instructions; ensure all three queries finish
	result["plays"] = <-plays_result
	result["minutes_played"] = <-duration_result
	result["artists"] = <-artists_result

	return result
}
