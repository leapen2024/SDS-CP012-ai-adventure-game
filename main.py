from routers.chat_openrouter import ChatOpenRouter
from langchain.schema import SystemMessage, HumanMessage, AIMessage
import asyncio
import os
from utils.config import load_environment_variables, get_api_key
import logging
from pathlib import Path
from typing import List
from langchain.schema import BaseMessage
from pydantic import SecretStr
from enum import Enum
from routers.chat_openai import ChatOpenAIProvider

class ChatProvider(Enum):
    OPENAI = "openai"
    OPENROUTER = "openrouter"

class ChatConfig:
    """Configuration class for chat parameters"""
    def __init__(self, 
                 provider: ChatProvider = ChatProvider.OPENROUTER,
                 openrouter_model: str = "gryphe/mythomax-l2-13b:free",
                 openai_model: str = "gpt-4o-mini",
                 system_prompt_path: str = "templates/system_prompt.md",
                 max_history: int = 6):
        self.provider = provider
        self.openrouter_model = openrouter_model
        self.openai_model = openai_model
        self.system_prompt_path = system_prompt_path
        self.max_history = max_history

def get_chat_provider(provider: ChatProvider, model_name: str, api_key: SecretStr, **kwargs):
    """Factory function to get the appropriate chat provider"""
    if provider == ChatProvider.OPENAI:
        return ChatOpenAIProvider(
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
    elif provider == ChatProvider.OPENROUTER:
        return ChatOpenRouter(
            model_name=model_name,
            api_key=api_key,
            **kwargs
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")

async def main():
    # Load environment variables
    load_environment_variables()
    
    # Initialize configuration (can be modified or loaded from config file)
    config = ChatConfig(
        provider=ChatProvider.OPENROUTER,
        system_prompt_path="templates/system_prompt.md",
        max_history=10
    )
    
    # Get model name based on provider
    model_name = config.openrouter_model if config.provider == ChatProvider.OPENROUTER else config.openai_model
    
    # Get the appropriate API key based on provider
    api_key_env = 'OPENROUTER_API_KEY' if config.provider == ChatProvider.OPENROUTER else 'OPENAI_API_KEY'
    api_key = SecretStr(get_api_key(api_key_env))
    
    # Initialize the chat provider
    storyteller = get_chat_provider(
        provider=config.provider,
        model_name=model_name,
        api_key=api_key
    )
    
    # Read system prompt and character setup prompts
    prompt_path = Path(config.system_prompt_path)
    character_setup_path = Path("templates/character_setting_setup.md")
    
    try:
        with open(prompt_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()
        with open(character_setup_path, "r", encoding="utf-8") as f:
            character_setup_prompt = f.read().strip()
    except FileNotFoundError as e:
        logging.error(f"Prompt file not found: {e.filename}")
        raise

    # Initialize message history with system prompt
    messages: List[BaseMessage] = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=character_setup_prompt)
    ]

    # Get character and setting options
    options_response = storyteller.invoke(messages)
    options_text = options_response.content
    print("\n=== Character and Setting Options ===")
    print(options_text)
    messages.append(AIMessage(content=options_text))

    # Get user's selection
    user_selection = input("Please choose a character and setting from the options above: ")
    messages.append(HumanMessage(content=user_selection))

    # Now start the adventure
    messages.append(HumanMessage(content="Start the adventure with the selected character and setting!"))

    try:
        while True:
            # Generate story continuation
            response = storyteller.invoke(messages)
            story_text = response.content
            print(story_text)
            
            # Add AI response to message history
            messages.append(AIMessage(content=story_text))
            
            # Get player input
            user_input = input("What would you like to do? (or type 'quit' to end): ")
            
            if user_input.lower() == 'quit':
                print("\nThanks for playing!")
                break
            
            # Add user input to message history
            messages.append(HumanMessage(content=user_input))
            
            # Maintain conversation history
            if len(messages) > config.max_history:
                messages = [messages[0]] + messages[-(config.max_history-1):]
    
    except Exception as e:
        print(f"An error occurred: {e}")
        logging.error(f"Error in main loop: {str(e)}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(main())