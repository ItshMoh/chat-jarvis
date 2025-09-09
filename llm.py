from tidb import db_manager
import requests
import os
import json
from dotenv import load_dotenv
from llmclient import client

load_dotenv()

class LLMManager:

    def __init__(self):
        self.API_BASE_URL = os.getenv('API_BASE_URL', 'https://api.openai.com/v1')
        self.API_KEY = os.getenv('OPENAI_API_KEY')
        return 
    
    async def get_tools(self):
        """Get available tools using FastMCP client"""
        try:
            async with client:
                tools_response = await client.list_tools()
                available_functions = []
                
                for tool in tools_response:
                    func = {
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": {
                                "type": "object",
                                "properties": tool.inputSchema.get("properties", {}),
                                "required": tool.inputSchema.get("required", []),
                            },
                        },
                    }
                    available_functions.append(func)
                
                return available_functions
        except Exception as e:
            print(f"Error getting tools: {str(e)}")
            return []

    async def handle_tool_calls(self, tool_calls):
        """Handle tool calls using FastMCP client"""
        tool_responses = []
        
        try:
            async with client:
                for tool_call in tool_calls:
                    function_name = tool_call["function"]["name"]
                    function_args = json.loads(tool_call["function"]["arguments"]) if isinstance(tool_call["function"]["arguments"], str) else tool_call["function"]["arguments"]
                    
                    print(f"Calling tool: {function_name} with args: {function_args}")
                    
                    # Call tool using FastMCP client
                    tool_result = await client.call_tool(name=function_name, arguments=function_args)
                    
                    result_text = ""
                    
                    if hasattr(tool_result, 'content') and tool_result.content:
                        for content in tool_result.content:
                            if hasattr(content, 'text'):
                                result_text += content.text
                    elif hasattr(tool_result, 'structured_content') and tool_result.structured_content:
                        result_text = json.dumps(tool_result.structured_content)
                    else:
                        result_text = "No result"
                    
                    tool_responses.append({
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": function_name,
                        "content": result_text
                    })
            
            return tool_responses
        except Exception as e:
            print(f"Error handling tool calls: {str(e)}")
            return []

    def make_chat_completion_request(self, messages, tools=None, tool_choice="auto"):
        """Make a direct API request to chat completions endpoint with detailed logging"""
        url = f"{self.API_BASE_URL}/chat/completions"
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.API_KEY}" if self.API_KEY and self.API_KEY.strip() else "Bearer dummy"
        }
        
        payload = {
            "model": os.getenv('LLM_MODEL', 'gpt-4o'),
            "messages": messages,
            "temperature": float(os.getenv('TEMPERATURE', "0.7")),
            "max_tokens": int(os.getenv('MAX_TOKENS', "1500"))
        }
        
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice
        
        try:
            response = requests.post(
                url, 
                headers=headers, 
                data=json.dumps(payload), 
                timeout=60
            )
            
            response_data = None
            try:
                response_data = response.json()
            except json.JSONDecodeError:
                print("Failed to decode JSON response")
                
            response.raise_for_status()
            return response_data if response_data else response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"API request failed: {str(e)}")
            raise Exception(f"API request failed: {str(e)}")
    
    async def reply_query(self, question, message):
        """Generate response using OpenAI with chat history context and tool support"""
        channel_id = str(message.channel.id)
        author = str(message.author)
        
        # Get chat history
        chat_history = db_manager.get_chat_history(channel_id, limit=10)
        
        # Build context for OpenAI
        messages = [
            {"role": "system", "content": "You are Jarvis, a helpful Discord bot. Respond conversationally based on the chat context. You have access to tools that can search through uploaded documents. Use the get_context tool when users ask questions that might be answered by documents they've shared. Don't give very long answers, try to answer in less than 1500 words."}
        ]
        
        # Add chat history as context
        for chat in chat_history:
            if chat['author'] == 'bot':
                messages.append({"role": "assistant", "content": chat['content']})
            else:
                content = f"{chat['author']}: {chat['content']}"
                if chat['referenced_message_id']:
                    ref_msg = db_manager.get_referenced_message(chat['referenced_message_id'])
                    if ref_msg:
                        content = f"[Replying to {ref_msg['author']}: {ref_msg['content']}] {content}"
                messages.append({"role": "user", "content": content})
        
        # Add current question
        current_content = f"{author}: {question}"
        if message.reference:
            ref_msg = db_manager.get_referenced_message(str(message.reference.message_id))
            if ref_msg:
                current_content = f"[Replying to {ref_msg['author']}: {ref_msg['content']}] {current_content}"
        
        messages.append({"role": "user", "content": current_content})
        
        try:
            # Get available tools
            available_functions = await self.get_tools()
            
            # Make initial completion request
            completion_response = self.make_chat_completion_request(
                messages=messages,
                tools=available_functions,
                tool_choice="auto"
            )
            
            assistant_message = completion_response["choices"][0]["message"]
            tool_calls = None
            tool_responses = []
            
            # Handle tool calls if present
            if assistant_message.get("tool_calls"):
                tool_calls = assistant_message["tool_calls"]
                tool_responses = await self.handle_tool_calls(assistant_message["tool_calls"])
                
                # Add assistant message with tool calls
                messages.append({
                    "role": "assistant",
                    "content": assistant_message.get("content"),
                    "tool_calls": assistant_message["tool_calls"]
                })
                
                # Add tool responses
                for tool_response in tool_responses:
                    messages.append(tool_response)
                
                # Make final completion request
                final_completion_response = self.make_chat_completion_request(
                    messages=messages,
                    tools=available_functions,
                    tool_choice="auto"
                )
                
                final_message = final_completion_response["choices"][0]["message"]
                response_text = final_message["content"]
            else:
                response_text = assistant_message["content"]
            
            print(f"LLM response: {response_text}")
            return response_text
            
        except Exception as e:
            print(f"LLM error: {e}")
            return "Sorry, I'm having trouble processing your request right now."

llmManager = LLMManager()