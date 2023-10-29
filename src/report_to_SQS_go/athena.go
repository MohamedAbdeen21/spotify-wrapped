package main

import (
	"context"
	"errors"
	"fmt"
	"log"
	"strconv"
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
	Type   int
	Sql    string
	Result chan []map[string]any
}

func GetResults(client *athena.Client, QueryID *string) ([]types.Row, error) {

	executionParams := &athena.GetQueryExecutionInput{
		QueryExecutionId: QueryID,
	}

	// poll query state, if success get results and return
	for {
		out, _ := client.GetQueryExecution(context.TODO(), executionParams)

		switch out.QueryExecution.Status.State {
		case types.QueryExecutionStateQueued, types.QueryExecutionStateRunning:
			time.Sleep(2 * time.Second)
		case types.QueryExecutionStateCancelled, types.QueryExecutionStateFailed:
			return nil, errors.New("Query failed")
		case types.QueryExecutionStateSucceeded:
			resultsParams := &athena.GetQueryResultsInput{
				QueryExecutionId: QueryID,
			}

			data, _ := client.GetQueryResults(context.TODO(), resultsParams)
			return data.ResultSet.Rows, nil
		}
	}
}

func ExecuteQuery(client *athena.Client, query Query) {
	cntxt := &types.QueryExecutionContext{
		Catalog:  aws.String(athena_catalog),
		Database: aws.String(athena_database),
	}

	conf := &types.ResultConfiguration{
		OutputLocation: aws.String(s3_athena_spill),
	}

	params := &athena.StartQueryExecutionInput{
		QueryString:           aws.String(query.Sql),
		ResultConfiguration:   conf,
		QueryExecutionContext: cntxt,
	}

	result := query.Result

	resp, err := client.StartQueryExecution(context.TODO(), params)
	if err != nil {
		log.Fatalln(err.Error())
		close(result)
		return
	}

	queryId := resp.QueryExecutionId
	query_result, err := GetResults(client, queryId)

	if err != nil {
		log.Fatalln(err.Error())
		close(result)
		return
	}

	var rows []map[string]any

	switch query.Type {
	case plays:
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

	case artists:
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

	case duration:
		for _, value := range query_result[1:] {
			duration_seconds_f, _ := strconv.ParseFloat(*value.Data[0].VarCharValue, 64)
			duration_second := int(duration_seconds_f)
			row := map[string]any{
				"duration": duration_second / 60,
			}
			rows = append(rows, row)
			result <- rows
		}
	}

	close(result)
}

func GetUserData(client *athena.Client, user string) map[string]any {
	result := make(map[string]any)

	filter := fmt.Sprintf(`WHERE email='%s'
				AND CAST("timestamp" AS INT) < %d
				AND CAST("timestamp" AS INT) > %d`,
		user, time.Now().Unix(), time.Now().Unix()-(3600*24*7))

	plays_query := Query{
		Type: plays,
		Sql: fmt.Sprintf(`SELECT name, COUNT(*), SUM(duration_seconds) AS total_time, image
			    FROM %s
          %s
			    GROUP BY (name, image)
			    ORDER BY total_time
			    DESC LIMIT 5`, history_table, filter),
		Result: make(chan []map[string]any),
	}

	duration_query := Query{
		Type:   duration,
		Sql:    fmt.Sprintf("SELECT SUM(duration_seconds) FROM %s %s", history_table, filter),
		Result: make(chan []map[string]any),
	}

	artists_query := Query{
		Type: artists,
		Sql: fmt.Sprintf(`SELECT artist, count(artist), sum(duration_seconds) as total
			    FROM %s, unnest(artists) as t(artist)
			    %s
			    GROUP BY artist
			    ORDER BY total
			    DESC LIMIT 5`, history_table, filter),
		Result: make(chan []map[string]any),
	}

	result["email"] = user

	go ExecuteQuery(client, plays_query)
	go ExecuteQuery(client, duration_query)
	go ExecuteQuery(client, artists_query)

	// blocking instructions; ensure all three queries finish
	result["plays"] = <-plays_query.Result
	result["minutes_played"] = (<-duration_query.Result)[0]["duration"]
	result["artists"] = <-artists_query.Result

	return result
}
