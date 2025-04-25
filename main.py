from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import json
import time

app = FastAPI()

LIVY_URL = "http://ec2-34-236-36-186.compute-1.amazonaws.com:8998"




class CodeExecutionRequest(BaseModel):
    session_id: int
    code: str

@app.get("/result/{session_id}/{statement_id}")
def get_result(session_id: int, statement_id: int):
    try:
        response = requests.get(f"{LIVY_URL}/sessions/{session_id}/statements/{statement_id}")
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print("❌ Error fetching result:", e)
        raise HTTPException(status_code=500, detail="Error fetching statement result from Livy")



@app.post("/execute_and_wait")
def execute_and_wait(request: CodeExecutionRequest):
    payload = {
        "code": request.code
    }
    try:
        # Submit the code
        response = requests.post(
            f"{LIVY_URL}/sessions/{request.session_id}/statements",
            headers={"Content-Type": "application/json"},
            data=json.dumps(payload)
        )
        response.raise_for_status()
        statement = response.json()
        statement_id = statement["id"]

        # Poll for result
        for _ in range(30):  # wait up to ~30 seconds
            time.sleep(1)
            result_response = requests.get(
                f"{LIVY_URL}/sessions/{request.session_id}/statements/{statement_id}"
            )
            result_response.raise_for_status()
            result = result_response.json()

            if result["state"] == "available" and result.get("output"):
                return {"result": result["output"]}

        return {"detail": "Timeout waiting for statement to finish."}

    except requests.exceptions.RequestException as e:
        print("❌ Error during execute_and_wait:", e)
        raise HTTPException(status_code=500, detail="Error communicating with Livy")