import json
from lesson_03_data_validation import UserValidator

with open("user_data.json", "r") as file:
    data = json.load(file)
    validated_user = UserValidator.model_validate(data, strict=True)
    print(validated_user)
