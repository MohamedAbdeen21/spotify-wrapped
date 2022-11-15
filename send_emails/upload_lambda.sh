pip install --platform manylinux2014_x86_64 --target=send_emails --implementation cp --python 3.9 --only-binary=:all: --upgrade -r ./requirements.txt

cp lambda_function.py send_emails

cd send_emails && zip -r ../send_emails.zip .

aws lambda update-function-code --function-name send_emails --zip-file fileb://../send_emails.zip

rm -rf send_emails send_emails.zip
