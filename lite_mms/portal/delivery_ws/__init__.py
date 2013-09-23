from flask import Blueprint

delivery_ws = Blueprint("delivery_ws", __name__, static_folder="static",
                        template_folder="templates")

from lite_mms.apis.auth import load_user_from_token
delivery_ws.before_request(load_user_from_token)

from lite_mms.portal.delivery_ws import webservices

