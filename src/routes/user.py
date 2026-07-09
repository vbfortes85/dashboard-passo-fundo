from flask import Blueprint
user_bp = Blueprint('user', __name__)
@user_bp.route('/health')
def health():
    return {'status': 'ok'}
