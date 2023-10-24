package main

import (
	"context"
	"log"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/feature/dynamodb/attributevalue"
	"github.com/aws/aws-sdk-go-v2/service/dynamodb"
)

type User struct {
	Email         string
	Refresh_token string
	Token         string
}

func GetUsers(svc *dynamodb.Client) (users []string) {

	out, err := svc.Scan(context.TODO(), &dynamodb.ScanInput{
		TableName: aws.String(tokens_table),
	})

	if err != nil {
		panic(err)
	}

	var rows []User

	err = attributevalue.UnmarshalListOfMaps(out.Items, &rows)
	if err != nil {
		log.Fatalf("Marshal error found: %s\n", err.Error())
	}

	for _, row := range rows {
		users = append(users, row.Email)
	}

	log.Printf("Found %d users\n", len(users))
	return users
}
