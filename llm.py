from tidb import db_manager
import requests
import os

from dotenv import load_dotenv
load_dotenv()

class LLMManager:

    def __init__(self):
        return 
    
    async def reply_query(self,question, message):
        """Generate response using OpenAI with chat history context"""
        channel_id = str(message.channel.id)
        author = str(message.author)
        
        # Get chat history
        chat_history = db_manager.get_chat_history(channel_id, limit=10)
        
        # Build context for OpenAI
        messages = [
            {"role": "system", "content": "You are Jarvis, a helpful Discord bot. Respond conversationally based on the chat context. Don't give very long Answer try to answer it in less than 1500 words."}
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
            headers = {
                'Authorization': f'Bearer {os.getenv("OPENAI_API_KEY")}',
                'Content-Type': 'application/json'
            }
            
            payload = {
                'model': 'gpt-4o',
                'messages': messages,
                'max_tokens': 500,
                'temperature': 0.7
            }
            
            response = requests.post(
                'https://api.openai.com/v1/chat/completions',
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                result = response_data['choices'][0]['message']['content'].strip()
                print(f"OpenAI API response: {result} \n")
                return response_data['choices'][0]['message']['content'].strip()
            else:
                print(f"OpenAI API error: {response.status_code} - {response.text}")
                return "Sorry, I'm having trouble processing your request right now."

        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "Sorry, I'm having trouble processing your request right now."



llmManager = LLMManager()