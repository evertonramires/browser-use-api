"""
Connect to your existing Chrome browser so it's logged into your websites
"""

import asyncio
import os
import sys

from browser_use.llm.azure.chat import ChatOpenAILike

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv

load_dotenv()

from browser_use import Agent, Browser, ChatGoogle


def select_chrome_profile() -> str | None:
	"""Prompt user to select a Chrome profile."""
	profiles = Browser.list_chrome_profiles()
	if not profiles:
		return None

	print('Available Chrome profiles:')
	for i, p in enumerate(profiles, 1):
		print(f'  {i}. {p["name"]}')

	while True:
		choice = 1
		# choice = input(f'\nSelect profile (1-{len(profiles)}): ').strip()
		# if choice.isdigit() and 1 <= int(choice) <= len(profiles):
		return profiles[int(choice) - 1]['directory']
		print('Invalid choice, try again.')


async def main():
	profile = select_chrome_profile()
	browser = Browser.from_system_chrome(profile_directory=profile, highlight_elements=True)

	agent = Agent(
		llm=ChatOpenAILike(model='browser',base_url=os.getenv('OPENAI_ENDPOINT'), api_key=os.getenv('OPENAI_API_KEY')),
		task='pick a random news portal and tell me 3 random news from today',
		browser=browser,
	)
	
	await agent.run()


if __name__ == '__main__':
	asyncio.run(main())
