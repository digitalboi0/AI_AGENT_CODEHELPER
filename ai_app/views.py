# api/views.py
from django.shortcuts import render
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import ParseError
from decouple import config
import logging
import uuid

from .ai import Ai_Agent

logger = logging.getLogger("ai")

# Cache BASE_URL at module level (loaded once)
BASE_URL = config("BASE_URL", default="https://aiagentcodehelper-production.up.railway.app")


def blog(request):
    """Render blog page"""
    return render(request, "blog.html")


def doc(request):
    """Render documentation page"""
    return render(request, "doc.html")


def get_agent_info(request):
    """
    Agent discovery endpoint - returns agent metadata
    GET /.well-known/agent.json
    """
    agent_info = {
        "name": "CodeHelperAgent",
        "description": "An AI agent to help with coding questions in Python, Django, and JavaScript.",
        "url": f"{BASE_URL.rstrip('/')}/api/",
        "provider": {
            "organization": "HNG Internship",
            "url": "https://hng.tech/"
        },
        "version": "1.0.0",
        "documentationUrl": f"{BASE_URL}/api/docs",
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
                        "input": {
                            "parts": [{"type": "text", "text": "How do I loop through a list in Python?"}]
                        },
                        "output": {
                            "parts": [{
                                "type": "text",
                                "text": "You can loop through a list using a `for` loop:\n```python\nmy_list = ['item1', 'item2', 'item3']\nfor item in my_list:\n    print(item)\n```\nThis iterates over each element (`item`) in `my_list`."
                            }]
                        }
                    },
                    {
                        "input": {
                            "parts": [{"type": "text", "text": "How do I create a Django model?"}]
                        },
                        "output": {
                            "parts": [{
                                "type": "text",
                                "text": "In Django, you create a model by subclassing `models.Model` in your `models.py`:\n```python\nfrom django.db import models\nclass MyModel(models.Model):\n    name = models.CharField(max_length=100)\n    description = models.TextField(blank=True)\n    created_at = models.DateTimeField(auto_now_add=True)\n    def __str__(self):\n        return self.name\n```\nRemember to create and run migrations after defining your model:\n```bash\npython manage.py makemigrations\npython manage.py migrate\n```"
                            }]
                        }
                    }
                ]
            }
        ]
    }

    logger.info("Serving Agent Card at /.well-known/agent.json")
    return JsonResponse(agent_info, status=200)


class GetResponse(APIView):
    """
    Main A2A JSON-RPC endpoint
    POST /api/
    """

    def post(self, request, *args, **kwargs):
        """Handle incoming A2A requests from Telex IM"""
        
        # Initialize variables
        request_id = None
        jsonrpc_version = "2.0"
        
        try:
            logger.info("Receiving A2A request from Telex IM")
            data = request.data
            
            # Extract core fields
            jsonrpc_version = data.get("jsonrpc", "2.0")
            request_id = data.get("id")
            request_method = data.get("method")
            params = data.get("params", {})
            
            # Validate JSON-RPC version
            if jsonrpc_version != "2.0":
                logger.warning(f"Invalid JSON-RPC version: {jsonrpc_version}")
                return self._error_response(
                    request_id, -32600,
                    f"Invalid Request: Unsupported JSON-RPC version '{jsonrpc_version}'"
                )
            
            # Route by method
            if request_method == "message/send":
                return self._handle_message_send(request_id, params)
            else:
                logger.warning(f"Unknown method: {request_method}")
                return self._error_response(
                    request_id, -32601,
                    f"Method not found: {request_method}"
                )
        
        except ParseError as e:
            logger.error(f"Parse error: {e}")
            return self._error_response(None, -32700, f"Parse error: {str(e)}")
        
        except Exception as e:
            logger.critical(f"Unexpected error: {e}", exc_info=True)
            return self._error_response(
                request_id, -32603,
                f"Internal server error: {str(e)}"
            )
    
    def _handle_message_send(self, request_id, params):
        """Handle message/send method"""
        
        # Validate message structure
        message = params.get("message", {})
        if not isinstance(message, dict):
            return self._error_response(
                request_id, -32600,
                "Invalid Request: 'params.message' is not an object"
            )
        
        message_id = message.get("messageId")
        parts = message.get("parts", [])
        
        # Validate parts
        if not isinstance(parts, list) or not parts:
            return self._error_response(
                request_id, -32600,
                "Invalid Request: 'params.message.parts' is missing or empty"
            )
        
        # Extract first part
        first_part = parts[0]
        if not isinstance(first_part, dict):
            return self._error_response(
                request_id, -32600,
                "Invalid Request: First message part is not an object"
            )
        
        # Check part type
        part_type = first_part.get("type") or first_part.get("kind")
        if part_type != "text":
            return self._error_response(
                request_id, -32600,
                f"Invalid Request: First message part type must be 'text', got '{part_type}'"
            )
        
        # Extract user text
        user_text = first_part.get("text", "").strip()
        if not user_text:
            return self._error_response(
                request_id, -32600,
                "Invalid Request: User text is empty"
            )
        
        logger.info(f"Processing message (ID: {request_id}): '{user_text[:50]}...'")
        
        # Process with AI
        try:
            ai_agent = Ai_Agent()
            ai_response = ai_agent.gemini_response(user_text)
        except Exception as e:
            logger.error(f"AI agent error: {e}", exc_info=True)
            return self._error_response(
                request_id, -32603,
                "AI agent is unreachable at the moment"
            )
        
        # Build response
        return self._build_success_response(
            request_id, message_id, user_text, ai_response, part_type
        )
    
    def _build_success_response(self, request_id, message_id, user_text, ai_response, part_type):
        """Build successful A2A response"""
        
        response_message_id = str(uuid.uuid4())
        task_id = str(uuid.uuid4())
        
        parts_response = [{
            "type": part_type,
            "text": ai_response
        }]
        
        result = {
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
            "artifacts": [
                {
                    "name": "agent_response",
                    "parts": [{"type": "text", "text": ai_response}]
                },
                {
                    "name": "original_query",
                    "parts": [{"type": "text", "text": user_text}]
                }
            ],
            "history": [
                {
                    "id": request_id,
                    "role": "user",
                    "parts": [{"type": part_type, "text": user_text}],
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
        }
        
        logger.info("Sending A2A response back to Telex IM")
        
        return Response({
            "jsonrpc": "2.0",
            "id": request_id,
            "result": result
        }, status=200)
    
    def _error_response(self, request_id, code, message):
        """Build JSON-RPC error response"""
        
        logger.debug(f"Error response: ID={request_id}, Code={code}, Message={message}")
        
        return Response({
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": code,
                "message": message
            }
        }, status=200)