package main

import (
	"context"
	"encoding/json"
	"log"
	"sync"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/athena"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
)

var wg sync.WaitGroup

func Handle(athena_client *athena.Client, user string, data chan map[string]any) {
	log.Println("Started gathering for user " + user)
	user_data := GetUserData(athena_client, user)
	log.Printf("Response retrieved for user: %s\n", user)
	data <- user_data
	wg.Done()
}

func LambdaHandler() (string, error) {

	var dataChannels []chan map[string]any
	var result []any

	cfg, err := config.LoadDefaultConfig(context.TODO(), func(o *config.LoadOptions) error {
		o.Region = "me-south-1"
		return nil
	})

	if err != nil {
		panic(err)
	}
	dynamo_client := dynamodb.NewFromConfig(cfg)
	athena_client := athena.NewFromConfig(cfg)

	users := GetUsers(dynamo_client)

	for _, user := range users {
		wg.Add(1)
		data := make(chan map[string]any, 1)
		dataChannels = append(dataChannels, data)
		go Handle(athena_client, user, data)
	}
	wg.Wait()

	for _, channel := range dataChannels {
		result = append(result, <-channel)
		close(channel)
	}
	data, err := json.Marshal(result)
	return string(data), err
}

func main() {
	lambda.Start(LambdaHandler)
}
