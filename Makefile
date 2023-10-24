init:
	cd deploy && terraform init

upgrade:
	cd deploy && terraform init -upgrade

destroy:
	cd deploy && terraform destroy -auto-approve

apply:
	cd src/report_to_SQS_go && env GOOS=linux GOARCH=amd64 CGO_ENABLED=0 go build -o main .
	cd deploy && terraform apply -auto-approve
	rm src/report_to_SQS_go/main.zip

plan:
	cd deploy && terraform plan 

restart:
	make destroy && make apply
