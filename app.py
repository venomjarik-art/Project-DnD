from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import random
import json
import os
 
app = FastAPI(title="D&D Cards") 
