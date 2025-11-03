from django.urls import path
from .views import GetResponse, get_agent_info, blog, doc



urlpatterns = [
    path(".well-known/agent.json", get_agent_info, name="get_agent_info"),
    path("work", GetResponse.as_view(), name="agent_work"),
    path("work/", GetResponse.as_view(), name="agent_work_slash"),
    path("blog/", blog, name="agent_blog_slash"),
    path("blog", blog, name="agent_blog"),
    path("doc", doc, name="agent_doc"),
    path("doc/", doc, name="agent_doc_slash"),
    
    
    ]
