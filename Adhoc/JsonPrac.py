import json


with open("abc.json", "r") as i:
    input_json = json.loads(i.read())
    print(input_json)
    with open("xyz.json", "w") as o:
        o.write(json.dumps(input_json))
