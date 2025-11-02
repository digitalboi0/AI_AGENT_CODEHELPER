from django.urls import path
from .views import GetResponse, get_agent_info


urlpatterns = [
    path(".well-known/agent.json", get_agent_info, name="get_agent_info"),
    path("work", GetResponse.as_view(), name="agent_work"),
    path("work/", GetResponse.as_view(), name="agent_work_slash"),
    ]
