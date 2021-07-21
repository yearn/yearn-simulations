import json

person = '{"name": "Bob", "languages": ["English", "Fench"]}'


with open('bot/registry.json') as f:
  data = json.load(f)
  person_dict = json.loads(person)
  print(person_dict)