package main

import (
	"context"
	"encoding/json"
	"fmt"
	"log"
	"os"
	"sync"

	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/athena"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
	"github.com/aws/aws-sdk-go-v2/service/sqs"
)

var wg sync.WaitGroup

func Handle(athena_client *athena.Client, sqs_client *sqs.Client, user string) {
	log.Println("Started gathering for user " + user)
	json_msg, _ := json.MarshalIndent(GetUserData(athena_client, user), "", " ")
	log.Printf("Response retrieved: %s\n", string(json_msg))
	sqs_client.SendMessage(context.TODO(), &sqs.SendMessageInput{
		MessageBody: aws.String(string(json_msg)),
		QueueUrl:    aws.String(os.Getenv("Queue_URL")),
	})

	wg.Done()
	fmt.Printf("%s\n", json_msg)
}

func LambdaHandler() {

	cfg, err := config.LoadDefaultConfig(context.TODO(), func(o *config.LoadOptions) error {
		o.Region = "me-south-1"
		return nil
	})

	if err != nil {
		panic(err)
	}
	dynamo_client := dynamodb.NewFromConfig(cfg)
	athena_client := athena.NewFromConfig(cfg)
	sqs_client := sqs.NewFromConfig(cfg)

	users := GetUsers(dynamo_client)

	for _, user := range users {
		wg.Add(1)
		go Handle(athena_client, sqs_client, user)
	}
	wg.Wait()
}

func main() {
	lambda.Start(LambdaHandler)
}
