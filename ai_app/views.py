# api/views.py
from django.shortcuts import render
import requests
from datetime import datetime, timezone
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from .ai import Ai_Agent
import hashlib
import copy
from django.http import JsonResponse, Http404
from decouple import config
import logging
from django.shortcuts import render
from django.db import IntegrityError
import uuid 
import re 

# Create your views here.

logger = logging.getLogger("ai")

EMAIL = config("Email")
NAME = config("Name")
STACK = config("Stack")

CAT_URL = config("Api_url")
REQUEST_TIMEOUT = config("Timeout", cast=int)

def blog(request):
    return render(request, "blog.html")

def doc(request):
    return render(request, "doc.html")

def get_agent_info(request):

    BASE_URL = config("BASE_URL", default=None)

    agent_info = {

        "name": "CodeHelperAgent",

        "description": "An AI agent to help with coding questions in Python, Django, and JavaScript.",

        "url": BASE_URL.rstrip('/') if BASE_URL else "https://aiagentcodehelper-production.up.railway.app/api/", # Base URL for A2A

        "provider": {

            "organization": "HNG Internship",

            "url": "https://hng.tech/"
        },

        "version": "1.0.0",

        "documentationUrl": "https://aiagentcodehelper-production.up.railway.app/api/docs", # Placeholder

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

        base_error_response = { 
                                "jsonrpc": "2.0",
                                "id": None, 
                                "error": {
                                    "code": -32600,
                                    "message": "Invalid Request"
                                }
                                }



        try:
            logger.info("Receiving A2A request from Telex IM...")
            telex_request_data = request.data 
            jsonrpc_version = telex_request_data.get("jsonrpc")
            request_id = telex_request_data.get("id") 
            request_method = telex_request_data.get("method") 
            params_data = telex_request_data.get("params", {}) 

        
            if jsonrpc_version != "2.0":
                logger.warning(f"Invalid JSON-RPC version: {jsonrpc_version}")
                error_resp = base_error_response.copy()
                error_resp["id"] = request_id 
                error_resp["error"]["code"] = -32600
                error_resp["error"]["message"] = f"Invalid Request: Unsupported JSON-RPC version '{jsonrpc_version}'"
                return Response(error_resp, status=status.HTTP_200_OK) 


            if request_method == "message/send":
                message_data = params_data.get("message", {})
                if not isinstance(message_data, dict):
                    logger.error("Malformed message parameter in A2A request.")
                    error_resp = base_error_response.copy()
                    error_resp["id"] = request_id
                    error_resp["error"]["code"] = -32600 
                    error_resp["error"]["message"] = "Invalid Request: 'params.message' is not an object."
                    return Response(error_resp, status=status.HTTP_200_OK)


                message_id = message_data.get("messageId") 

                parts_list = message_data.get("parts", []) 
                if not isinstance(parts_list, list) or len(parts_list) == 0:
                    logger.error("Malformed message parts in A2A request.")
                    error_resp = base_error_response.copy()
                    error_resp["id"] = request_id
                    error_resp["error"]["code"] = -32600 
                    error_resp["error"]["message"] = "Invalid Request: 'params.message.parts' is missing, not a list, or empty."
                    return Response(error_resp, status=status.HTTP_200_OK)

                first_part_data = parts_list[0] 
                if not isinstance(first_part_data, dict):
                    logger.error("First message part is not an object in A2A request.")
                    error_resp = base_error_response.copy()
                    error_resp["id"] = request_id
                    error_resp["error"]["code"] = -32600 
                    error_resp["error"]["message"] = "Invalid Request: First message part is not an object."
                    return Response(error_resp, status=status.HTTP_200_OK)

                part_type = first_part_data.get("type") or first_part_data.get("kind") 
                if part_type != "text": 
                    logger.error(f"First message part type is not 'text', got '{part_type}'.")
                    error_resp = base_error_response.copy()
                    error_resp["id"] = request_id
                    error_resp["error"]["code"] = -32600 
                    error_resp["error"]["message"] = f"Invalid Request: First message part type is not 'text', got '{part_type}'."
                    return Response(error_resp, status=status.HTTP_200_OK)

                user_text = first_part_data.get("text", "").strip() 

                if user_text: 
                    logger.info(f"Processing A2A message (Request ID: {request_id}, Message ID: {message_id}): '{user_text[:50]}...'")

                    try:
                        ai_agent = Ai_Agent()
                        ai_agent_response = ai_agent.gemini_response(user_text)
                        parts_response = [
                        {
                            "type" : part_type, 
                            "text" : ai_agent_response,

                        }
                    ]

                    except Exception as e:
                        logger.error(f"Error calling AI agent for message '{user_text[:50]}...': {e}", exc_info=True)
                        code = -32603
                        message = "AI AGENT is unreachable at the moment"
                        return self.error_response(jsonrpc_version, request_id, code, message) 

                else: # 
                    code = -32600
                    message = "Invalid data: user text is empty or contains only whitespace"
                    return self.error_response(jsonrpc_version, request_id, code, message)

            else: 
                logger.warning(f"Unknown method received in A2A request: {request_method}")
                error_resp = base_error_response.copy()
                error_resp["id"] = request_id 
                error_resp["error"]["code"] = -32601 
                error_resp["error"]["message"] = f"Method not found: {request_method}"
                return Response(error_resp, status=status.HTTP_200_OK)


        except ParseError as e: 
            logger.error(f"Error parsing JSON in A2A request body: {e}")
            error_resp = base_error_response.copy()
 
            error_resp["id"] = None 
            error_resp["error"]["code"] = -32700 
            error_resp["error"]["message"] = f"Parse error: {str(e)}"
            return Response(error_resp, status=status.HTTP_200_OK) 
        except Exception as e: 
            logger.critical(f"Unexpected error in GetResponse A2A view: {e}", exc_info=True)
            error_resp = base_error_response.copy()

            error_resp["id"] = request_id 
            error_resp["error"]["code"] = -32603 
            error_resp["error"]["message"] = f"Internal server error during A2A processing: {str(e)}"
            return Response(error_resp, status=status.HTTP_200_OK) 


        response_message_id = str(uuid.uuid4())

        task_id = str(uuid.uuid4())


        artifacts = [

            {
                "name": "agent_response",
                "parts": [
                    {
                        "type": "text",
                        "text": ai_agent_response
                    }
                ]
            },

            {
                "name": "original_query",
                "parts": [
                    {
                        "type": "text",
                        "text": user_text
                    }
                ]
            }

        ]
   
        history = [
       
            {
                "id": request_id, 
                "role": "user",
                "parts": [
                    {
                        "type": part_type, 
                        "text": user_text  
                    }
                ],
                "kind": "message", 
                "messageId": message_id 
            },
       
            {
                "id": task_id, 
                "role": "agent",
                "parts": parts_response, 
                "kind": "message", 
                "messageId": response_message_id 
            }
        ]
       
        result_data = {
            "id": task_id, 
            "contextId": message_id, 
            "status": {
                "state": "completed", 
                "message": { 
                    "role": "agent",
                    "parts": parts_response,
                    "kind": "message",
                    "messageId": response_message_id 
                }
            },
            "artifacts": artifacts, 
            "history": history 
        }



        logger.info("Sending A2A response back to Telex IM.")

        return Response({
            "jsonrpc" : jsonrpc_version, 
            "id" : request_id,          
            "result" : result_data 
        }, status=status.HTTP_200_OK) 


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
