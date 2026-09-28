from datetime import datetime, date
from flask import Blueprint, jsonify, request, g
from app.models.teacher import Teacher
from app.models.rule import PromotionRule
from app.models.post import TeachingPost
from app.services.promotion_engine import evaluate_eligibility
from app.services.qualifications_catalog import QUALIFICATIONS_CATALOG, PREDEFINED_INSTITUTES

api_bp = Blueprint('api', __name__)

@api_bp.route('/qualifications-catalog', methods=['GET'])
def get_qualifications_catalog():
    return jsonify({
        'catalog': QUALIFICATIONS_CATALOG,
        'institutes': PREDEFINED_INSTITUTES
    })

@api_bp.route('/teaching-posts', methods=['GET'])
def get_teaching_posts():
    cadre = request.args.get('cadre')
    bs = request.args.get('bs', type=int)
    active_only = request.args.get('active_only', 'true').lower() == 'true'

    query = g.db.query(TeachingPost)
    if active_only:
        query = query.filter(TeachingPost.is_active == True)
    if cadre:
        query = query.filter(TeachingPost.cadre == cadre)
    if bs:
        query = query.filter(TeachingPost.basic_scale == bs)

    posts = query.order_by(TeachingPost.basic_scale.asc(), TeachingPost.display_order.asc(), TeachingPost.post_title.asc()).all()

    grouped = {}
    for p in posts:
        if p.cadre not in grouped:
            grouped[p.cadre] = []
        grouped[p.cadre].append(p.to_dict())

    return jsonify({
        'success': True,
        'count': len(posts),
        'posts': [p.to_dict() for p in posts],
        'grouped_by_cadre': grouped
    })

@api_bp.route('/simulate', methods=['POST'])
def api_simulate():
    data = request.get_json() or {}
    teacher_id = data.get('teacher_id')
    rule_id = data.get('rule_id')
    as_of_date_str = data.get('as_of_date') or datetime.now().strftime('%Y-%m-%d')

    if not teacher_id or not rule_id:
        return jsonify({'error': 'teacher_id and rule_id are required'}), 400

    db = g.db
    teacher = db.query(Teacher).get(teacher_id)
    rule = db.query(PromotionRule).get(rule_id)

    if not teacher or not rule:
        return jsonify({'error': 'Teacher or Rule not found'}), 404

    as_of_date = datetime.strptime(as_of_date_str, '%Y-%m-%d').date()
    result = evaluate_eligibility(teacher, rule, as_of_date=as_of_date, db_session=db)
    return jsonify(result)
