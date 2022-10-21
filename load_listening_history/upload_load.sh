pip install --platform manylinux2014_x86_64 --target=load_listening_history --implementation cp --python 3.9 --only-binary=:all: --upgrade -r ./requirements.txt

cp lambda_function.py load_listening_history

cd load_listening_history && zip -r ../load_listening_history.zip .

aws lambda update-function-code --function-name load_listening_history --zip-file fileb://../load_listening_history.zip
