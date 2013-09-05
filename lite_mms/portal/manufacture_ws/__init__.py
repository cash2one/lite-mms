from flask import Blueprint

manufacture_ws = Blueprint("manufacture_ws", __name__, static_folder="static",
                             template_folder="templates")
from lite_mms.apis.auth import load_user_from_token
manufacture_ws.before_request(load_user_from_token)

from lite_mms.portal.manufacture_ws import webservices

