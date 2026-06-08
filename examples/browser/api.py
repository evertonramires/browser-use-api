import asyncio
import os
import sys
import uuid
from typing import Dict, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException
from pydantic import BaseModel

# Add the parent directory to sys.path just like real_browser.py
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

load_dotenv()

from browser_use import Agent, Browser
from browser_use.llm.azure.chat import ChatOpenAILike

app = FastAPI(title="Browser Use Agent API")

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
    except Exception as e:
        tasks[task_id]["status"] = "failed"
        tasks[task_id]["error"] = str(e)
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


if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
