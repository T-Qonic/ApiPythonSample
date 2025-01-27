from random import randint
import requests
import re
import uuid
from oauth import login


apiUrl = "https://api.qonic.com/v1/"

tokenResponse = login(
    issuer="https://release-qonic.eu.auth0.com",
    client_id="9Jtp6GGNqPPJzvqNKRoQJ66A9juVbE8A",
    redirect_uri="http://localhost:34362",
    scope="openid profile email",
    audience="https://api.qonic.com")

class ModificationInputError:
    def __init__(self, guid, field, error, description):
        self.guid = guid
        self.field = field
        self.error = error
        self.description = description
    def __str__(self):
        return f"{self.guid}: {self.field}: {self.error}: {self.description}"
    def __repr__(self):
        return f"{self.guid}: {self.field}: {self.error}: {self.description}"

class ApiError:
    def __init__(self, Error, ErrorDetails):
        self.error = Error
        self.details = ErrorDetails
    def __str__(self):
        return f"{self.error}: {self.details}"
    def __repr__(self):
        return f"{self.error}: {self.details}"

def handleErrorResponse(response: requests.Response):
    try:
        apiError = ApiError(**response.json())
        print(apiError)
    except Exception as err:
        print(f"Error occurred while processing error response: {err}")

def sendGetRequest(path, params=None):
    try:
        response = requests.get(f"{apiUrl}{path}", params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}"})
        response.raise_for_status()
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()
    return response.json()

def sendPostRequest(path, data=None, json=None, params=None, sessionId=str):
    try:
        response = requests.post(f"{apiUrl}{path}", data=data, json=json, params=params,  headers={"Authorization": f"Bearer {tokenResponse.access_token}", "X-Client-Session-Id": sessionId})
        response.raise_for_status()
        return response
    except requests.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        handleErrorResponse(response)
        exit()
    except Exception as err:
        print(f"Other error occurred: {err}")
        exit()

projectsJson = sendGetRequest("projects")
print("your projects:")
for project in projectsJson["projects"]:
    print(f"{project['id']} - {project['name']}")

print()
projectId = input("Enter a project id: ")
print()
    
modelsJson = sendGetRequest(f"projects/{projectId}/models")
print("your models:")
for model in modelsJson["models"]:
    print(f"{model['id']} - {model['name']}")

print()
modelId = input("Enter a model id: ")
print()

availableDataJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query-available-data")
print("fields:")
for field in availableDataJson["fields"]:
    print(f"{field}")
print()


print("Quering the Guid, Class, Name and FireRating fields, filtered on Class Beam...")
print()
# Query the Guid, Class, Name and FireRating fields
fieldsStr = "Guid Class Name FireRating"
params = list(map(lambda field: ("fields", field), re.split(r'[;,\s]+', fieldsStr)))
# Filter on class Beam
params.append(("filters[Class]", "Beam"))
propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print()
for row in propertiesJson["result"]:
    print(f"{row}")

print()

print("Starting modification session")
sessionId = str(uuid.uuid4())
sendPostRequest(f"projects/{projectId}/models/{modelId}/start-session", sessionId=sessionId)
try:
    fireRating = f"F{randint(1, 200)}"
    print(f"Modifying FireRating of first row to {fireRating}")
    changes = {
        "values": {
            "FireRating": {
                propertiesJson["result"][0]["Guid"]: {
                    "PropertySet": "Pset_BeamCommon",
                    "Value": fireRating
                }
            }
        }
    }
    response = sendPostRequest(f"projects/{projectId}/models/{modelId}/external-data-modification", json=changes, sessionId=sessionId)
    errors =  list(map(lambda json: ModificationInputError(**json), response.json()["errors"]))
    if len(errors) > 0:
        print(str(errors))
        exit()
finally:
    print("Closing modification session")
    sendPostRequest(f"projects/{projectId}/models/{modelId}/end-session", sessionId=sessionId)
print("Modification is done")
print()
print("Quering data again")

propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print("Showing only the first row:")
print(propertiesJson["result"][0])

print()
print("Starting modification session to reset value")
sessionId = str(uuid.uuid4())
sendPostRequest(f"projects/{projectId}/models/{modelId}/start-session", sessionId=sessionId)
try:
    fireRating = f"F{randint(1, 200)}"
    print(f"Clearing FireRating of first row")
    changes = {
        "values": {
            "FireRating": {
                propertiesJson["result"][0]["Guid"]: None
            }
        }
    }
    response = sendPostRequest(f"projects/{projectId}/models/{modelId}/external-data-modification", json=changes, sessionId=sessionId)
    errors =  list(map(lambda json: ModificationInputError(**json), response.json()["errors"]))
    if len(errors) > 0:
        print(errors)
        exit()
finally:
    print("Closing modification session")
    sendPostRequest(f"projects/{projectId}/models/{modelId}/end-session", sessionId=sessionId)
print("Modification is done")
print()
print("Quering data again")

propertiesJson = sendGetRequest(f"projects/{projectId}/models/{modelId}/external-query", params)

print("Showing only the first row:")
print(propertiesJson["result"][0])