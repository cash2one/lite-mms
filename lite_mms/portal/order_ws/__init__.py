from flask import Blueprint

order_ws = Blueprint("order_ws", __name__, static_folder="static",
    template_folder="templates")

from lite_mms.apis.auth import load_user_from_token
order_ws.before_request(load_user_from_token)

from lite_mms.portal.order_ws import webservices

