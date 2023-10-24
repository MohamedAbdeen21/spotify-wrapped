pip install --platform manylinux2014_x86_64 --target=registration --implementation cp --python 3.9 --only-binary=:all: --upgrade -r ./requirements.txt

cp lambda_function.py client.py registration

cd registration && zip -r ../registration.zip .

aws lambda update-function-code --function-name spotify-registration --zip-file fileb://../registration.zip

rm -r ../registration ../registration.zip
