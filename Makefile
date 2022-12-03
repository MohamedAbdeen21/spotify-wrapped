init:
	terraform init

upgrade:
	terraform init -upgrade

destroy:
	terraform destroy -auto-approve

apply:
	cd report_to_SQS_go && env GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o main .
	terraform apply -auto-approve
	rm report_to_SQS_go/main.zip

plan:
	terraform plan

restart:
	make destroy && make apply