env GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o main .

zip main.zip main

aws lambda update-function-code --function-name report_to_SQS_Go --zip-file fileb://./main.zip

rm main.zip main
