from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from .ai import Ai_Agent
import hashlib
import copy
from django.http import JsonResponse
from decouple import config
import logging
from django.shortcuts import render
# Create your views here.

logger = logging.getLogger("ai")

def blog(request):
    return render(request, "blog.html")

def doc(request):
    return render(request, "doc.html")

def get_agent_info(request):

    BASE_URL = config("BASE_URL", default=None)

    agent_info = {

        "name": "CodeHelperAgent", 

        "description": "An AI agent to help with coding questions in Python, Django, and JavaScript.", 

        "url": BASE_URL.rstrip('/') if BASE_URL else "https://aiagentcodehelper-production.up.railway.app/ai/work", 

        "provider": {

            "organization": "HNG Internship", 

            "url": "https://hng.tech/" 
        },

        "version": "1.0.0", 
  
        "documentationUrl": "https://aiagentcodehelper-production.up.railway.app/ai/docs", 
 
        "capabilities": {
            "streaming": False, 
            "pushNotifications": False, 
            "stateTransitionHistory": False 
        },
 
        "defaultInputModes": ["text/plain"], 
        "defaultOutputModes": ["text/plain", "application/json"], 

        "skills": [
            {
                "id": "coding_assistant", 

                "name": "Code Explanation & Snippets", 

                "description": "Explains programming concepts and provides code snippets for Python, Django, and JavaScript.", 

                "inputModes": ["text/plain"], 
                "outputModes": ["text/plain"], 
                "examples": [ 
                    {
 
                        "input": { "parts": [{ "type": "text", "text": "How do I loop through a list in Python?" }] },
                        "output": { "parts": [{ "type": "text", "text": "You can loop through a list using a `for` loop:\n```python\nmy_list = ['item1', 'item2', 'item3']\nfor item in my_list:\n    print(item)\n```\nThis iterates over each element (`item`) in `my_list`." }] }

                    },
                    {
                        
                        "input": { "parts": [{ "type": "text", "text": "How do I create a Django model?" }] },
                        "output": { "parts": [{ "type": "text", "text": "In Django, you create a model by subclassing `models.Model` in your `models.py`:\n```python\nfrom django.db import models\nclass MyModel(models.Model):\n    name = models.CharField(max_length=100)\n    description = models.TextField(blank=True)\n    created_at = models.DateTimeField(auto_now_add=True)\n    def __str__(self):\n        return self.name\n```\nRemember to create and run migrations after defining your model:\n```bash\npython manage.py makemigrations\npython manage.py migrate\n```" }] }
                        
                    }
                ]
            }
        ]
    }


    logger.info("Serving Agent Card at /.well-known/agent.json")
    return JsonResponse(agent_info, status=status.HTTP_200_OK, safe=True)




class GetResponse(APIView):
    def post(self, request, *args, **kwargs):
        
        error_response =  {
                                "jsonrpc": "2.0",
                                "id": 2,
                                "error": {
                                    "code": -32600, 
                                    "message": "Invalid Request"
                                } 
                                }
        
        
        
        try:
            logger.info("Receiving code assistance request from Telex IM...")
            telex_request_data = request.data
        except ParseError as e:
            logger.error(f"Error parsing JSON in request body: {e}")
            error_resp = error_response.copy()
            error_resp ["error"] ["message"] = "couldnt parse the data recived"
            error_resp ["error"] ["code"] = -32700

            return Response(
                error_resp,
                status=status.HTTP_400_BAD_REQUEST
                )
        except Exception as e:
            logger.critical(f"Unexpected error during request processing: {e}", exc_info=True)
            error_resp = error_response.copy()
            error_resp["error"]["message"] = f"some error occured while get data from telex {e}"
            error_resp ["error"] ["code"] = -32603
            return Response(error_resp, status=status.HTTP_502_BAD_GATEWAY)
            
            
        
        
        
        id = telex_request_data.get("id", None)
        method = telex_request_data.get("method", None)    
        jsonrpc = telex_request_data.get("jsonrpc", None)    
        params = telex_request_data.get("params", None)
        

        logger.debug(f"Extracted RPC data - ID: {id}, Method: {method}, JSONRPC: {jsonrpc}")
        if params is None:
            logger.warning("No params was found in the data")
            message = "Invalid data: no params was found in the data"
            jsonrpc = jsonrpc
            id = id
            code = -32600
            
            return self.error_response(jsonrpc, id, code, message)
            
        elif not isinstance(params, dict):
            jsonrpc = jsonrpc
            id = id 
            code = -32600
            message = "Invalid data: params wasnt passed as valid dict"
            
            return self.error_response(jsonrpc, id, code, message)
        
        message = params.get("message", None)
        if not message:
            jsonrpc = jsonrpc
            id = id
            code = -32600
            message = "Invalid data: no message was found in the params dict"
            return self.error_response(jsonrpc, id, code, message)
        if not isinstance(message, dict):
            jsonrpc = jsonrpc
            id = id
            code = -32600
            message = "Invalid data: message in params wasnt a valid dict"
            return self.error_response(jsonrpc, id, code, message)
        
        
        parts = message.get("parts", None)
        if not parts:
            jsonrpc = jsonrpc
            id = id
            code = -32600
            message = "Invalid data: there was not parts in message dict"
            return self.error_response(jsonrpc, id, code, message)
        if not isinstance(parts, list):
            jsonrpc = jsonrpc
            id = id
            code = -32600
            message = "Invalid data: parts wasnt a valid dict"
            return self.error_response(jsonrpc, id, code, message)
        
        if len(parts) == 0:
            jsonrpc = jsonrpc
            id = id
            code = -32600
            message = "Invalid data: parts is an empty list"
            return self.error_response(jsonrpc, id, code, message)
        
        if parts and isinstance(parts, list) and len(parts) > 0:
            parts_data = parts[0]
            first_data =  parts_data.get("type") or parts_data.get("kind")
            if first_data == "text" and len(parts_data) > 0:
                user_text = parts_data.get("text", None)
                method = telex_request_data.get("method")
                if user_text and isinstance(user_text, str) and len(user_text) > 0:
                    logger.info(f"Processing user message: '{user_text[:50]}...'")
                    try:
                        if method == "message/send":
                            try:
                                ai_agent = Ai_Agent()
                            except Exception as e:
                                logger.critical(f"Unable to init AI AGENT")
                                code = -32000
                                message = "Unable to init AI AGENT"
                                return self.error_response(jsonrpc, id, code, message)
                            
                            ai_agent_response = ai_agent.gemini_response(user_text)
                            parts_response = [
                            {
                                "type" : first_data,
                                "text" : ai_agent_response,
                                
                            }
                        ]
                        else:
                            return self.error_response(jsonrpc, id, code = -32601, message = "Unknow method")   
                    except Exception as e:
                        logger.error(f"Error calling AI agent for message '{user_text[:50]}...': {e}", exc_info=True)
                        code = -32603
                        message = "AI AGENT is unreachable at the moment"
                        return self.error_response(jsonrpc, id, code, message)
                else:
                    code = -32600
                    message = "Invalid data: user text is in a valid prompt or query"
                    return self.error_response(jsonrpc, id, code, message)   
            else: 
                code =-32600
                message = "Invalid data : the type is not a text"
                return self.error_response(jsonrpc, id, code, message)     
        else:
            code = -32600
            message = "Invalid data: the parts list is empty"
            return self.error_response(jsonrpc, id, code, message)            

        kind = "message"
        message_id = telex_request_data.get("message_id")
        
        
        logger.info("Sending code assistance response back to Telex IM.")
         
        return Response({
            "jsonrpc" : jsonrpc,
            "id" : id,
            "result" :{
                "role" : "agent",
                "parts" : parts_response,
                "kind" : kind,
                "message_id" : message_id
            }
        })
        
    def error_response(self, jsonrpc, id, code, message, *args, **kwargs):
        
        error_response =  {
                                "jsonrpc": jsonrpc ,
                                "id": id,
                                "error": {
                                    "code": code, 
                                    "message": message
                                } 
                                }
        logger.debug(f"Sending JSON-RPC error response: ID={id}, Code={code}, Message={message}")
        return Response(error_response, status=status.HTTP_200_OK)
        
        
    