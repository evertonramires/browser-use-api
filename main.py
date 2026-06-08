import asyncio
import os
import sys
import uuid
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
import threading
import time
import json
import urllib.request
import urllib.error

from telegram_connector import telegram_enabled, send_telegram_message, read_telegram_messages

load_dotenv()

from browser_use import Agent, Browser
from browser_use.llm.azure.chat import ChatOpenAILike

@asynccontextmanager
async def lifespan(app: FastAPI):
    if telegram_enabled():
        threading.Thread(target=poll_telegram, daemon=True).start()
    yield

app = FastAPI(title="Browser Use Agent API", lifespan=lifespan)

# Simple in-memory task store
# In a production environment, you would use a database (e.g., Redis, PostgreSQL)
tasks: Dict[str, dict] = {}


class TaskRequest(BaseModel):
    task: str


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # "pending", "running", "completed", "failed"
    result: Optional[str] = None
    error: Optional[str] = None


def select_chrome_profile() -> str | None:
    """Select the first available Chrome profile, adapted from real_browser.py."""
    profiles = Browser.list_chrome_profiles()
    if not profiles:
        return None
    
    # We automatically select the first profile since an API cannot prompt the user
    return profiles[0]['directory']


async def run_agent_task(task_id: str, task: str):
    tasks[task_id]["status"] = "running"
    send_telegram_message(f"🚀 Started task: {task}")
    browser = None
    try:
        profile = select_chrome_profile()
        browser = Browser.from_system_chrome(profile_directory=profile, highlight_elements=True)

        # Using ChatOpenAILike to exactly match real_browser.py
        # Note: ChatBrowserUse is generally recommended for best performance
        agent = Agent(
            llm=ChatOpenAILike(
                model='browser',
                base_url=os.getenv('OPENAI_ENDPOINT'),
                api_key=os.getenv('OPENAI_API_KEY')
            ),
            task=task,
            browser=browser,
        )

        history = await agent.run()
        
        tasks[task_id]["status"] = "completed"
        # The agent history contains the final extracted output
        tasks[task_id]["result"] = history.final_result()
        send_telegram_message(f"✅ Task completed!\n\nResult: {history.final_result()}")
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
        send_telegram_message(f"❌ Task failed!\n\nError: {str(e)}")
    finally:
        if browser:
            await browser.close()


@app.post("/task", response_model=TaskStatusResponse)
async def submit_task(request: TaskRequest, background_tasks: BackgroundTasks):
    """Submit a task to be executed by the AI agent."""
    task_id = str(uuid.uuid4())
    
    tasks[task_id] = {
        "status": "pending",
        "result": None,
        "error": None
    }
    
    # Schedule the task to run in the background
    background_tasks.add_task(run_agent_task, task_id, request.task)
    
    return TaskStatusResponse(
        task_id=task_id,
        status="pending"
    )


@app.get("/task/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(task_id: str):
    """Poll the status and result of a submitted task."""
    if task_id not in tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    
    task_data = tasks[task_id]
    return TaskStatusResponse(
        task_id=task_id,
        status=task_data["status"],
        result=task_data["result"],
        error=task_data["error"]
    )


def poll_telegram():
    while True:
        try:
            messages = read_telegram_messages()
            for msg in messages:
                url = "http://127.0.0.1:8000/task"
                data = json.dumps({"task": msg}).encode("utf-8")
                req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
                try:
                    urllib.request.urlopen(req, timeout=10)
                except Exception as e:
                    print(f"Failed to submit task from telegram: {e}")
        except Exception as e:
            print(f"Telegram polling error: {e}")
        time.sleep(2)


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
