# -*- coding: UTF-8 -*-
import json

from sqlalchemy import and_
from pyfeature import step

import lite_mms
from lite_mms import models
from lite_mms.basemain import app
from lite_mms.test.utils import login, client_login

@step(u'调度员对子订单进行预排产(\d+)公斤')
def _(step, weight, sub_order):
    with app.test_request_context():
        with app.test_client() as c:
            login('s', 's', c)
            rv = c.post('/order/work-command', 
                        data=dict(sub_order_id=sub_order.id, 
                                  schedule_weight=weight))
            assert rv.status_code == 302

@step(u'一条重量是(\d+)公斤的工单生成了')
def _(step, weight, sub_order):
    model = models.WorkCommand
    return model.query.filter(and_(model.org_weight==weight, model.sub_order_id==sub_order.id)).one()
    

@step(u'原子订单的剩余重量是(\d+)公斤')
def _(step, weight, sub_order):
    assert int(sub_order.resync().remaining_quantity) == int(weight)

@step(u'调度员将工单排产给车间')
def _(step, wc, department):
    with app.test_request_context():
        with app.test_client() as c:
            login('s', 's', c)
            rv = c.post('/manufacture/schedule', data=dict(department_id=department.id, id=wc.id)) 
            assert rv.status_code == 302

@step(u'车间主任将看到工单')
def _(step, wc, department):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('dl', 'dl', c)
            rv = c.get('/manufacture_ws/work-command-list?department_id=%s&status=%d&auth_token=%s' % (department.id, lite_mms.constants.work_command.STATUS_ASSIGNING, auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == wc.sub_order.order.goods_receipt.customer.name
            assert d['department']['id'] == department.id
            assert d['department']['name'] == department.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight

@step(u'车间主任将工单分配到班组')
def _(step, wc, department, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('dl', 'dl', c)
            rv = c.put('/manufacture_ws/work-command?work_command_id=%d&action=%d&team_id=%s&auth_token=%s' % (wc.id, lite_mms.constants.work_command.ACT_ASSIGN, team.id, auth_token))
            assert rv.status_code == 200

@step(u'班组长将看到工单')
def _(step, wc, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.get('/manufacture_ws/work-command-list?team_id=%s&status=%d&auth_token=%s' % (team.id, lite_mms.constants.work_command.STATUS_ENDING, auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == wc.sub_order.order.goods_receipt.customer.name
            assert d['team']['id'] == team.id
            assert d['team']['name'] == team.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight



@step(u'班组长增加重量(\d+)公斤, 并且结束')
def _(step, weight, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.put('/manufacture_ws/work-command?work_command_id=%d&action=%d&weight=%d&is_finished=1&auth_token=%s' % (wc.id, lite_mms.constants.work_command.ACT_ADD_WEIGHT, int(weight), auth_token))
            assert rv.status_code == 200

@step(u'班组长增加重量(\d+)公斤$')
def _(step, weight, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('tl', 'tl', c)
            rv = c.put('/manufacture_ws/work-command?work_command_id=%d&action=%d&weight=%d&auth_token=%s' % (wc.id, lite_mms.constants.work_command.ACT_ADD_WEIGHT, int(weight), auth_token))
            assert rv.status_code == 200

@step(u'工单的工序后重量是(\d+)公斤')
def _(step, weight, wc):
    assert wc.resync().processed_weight == int(weight)

@step(u'质检员可以看到工单')
def _(step, wc, team):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('qi', 'qi', c)
            rv = c.get('/manufacture_ws/work-command-list?status=%d&auth_token=%s' % (lite_mms.constants.work_command.STATUS_QUALITY_INSPECTING, auth_token))
            assert rv.status_code == 200
            d = json.loads(rv.data)['data'][0]
            assert d['customerName'] == wc.sub_order.order.goods_receipt.customer.name
            assert d['team']['id'] == team.id
            assert d['team']['name'] == team.name
            assert d['id'] == wc.id
            assert d['orderID'] == wc.sub_order.order.id
            assert d['subOrderId'] == wc.sub_order.id
            assert d['orgWeight'] == wc.org_weight

@step(u'质检员全部通过该工单')
def _(step, wc):
    with app.test_request_context():
        with app.test_client() as c:
            auth_token = client_login('qi', 'qi', c)
            rv = c.post('/manufacture_ws/quality-inspection-report?work_command_id=%d&quantity=%d&result=%d&auth_token=%s' % (wc.id, wc.processed_weight, lite_mms.constants.quality_inspection.FINISHED, auth_token))
            qir_id = json.loads(rv.data)['id']
            assert rv.status_code == 200
            rv = c.put('/manufacture_ws/work-command?work_command_id=%d&action=%d&auth_token=%s' % (wc.id, lite_mms.constants.work_command.ACT_QI, auth_token))
            assert rv.status_code == 200
            return models.QIReport.query.get(qir_id)

@step(u'该工单已经结束')
def _(step, wc):
    assert wc.resync().status == lite_mms.constants.work_command.STATUS_FINISHED

@step(u'一条对应的仓单生成了')
def _(step, qir, harbor):
    model = models.StoreBill
    return model.query.filter(and_(model.qir_id==qir.id, 
                                   model.weight==qir.weight, 
                                   model.harbor_name==harbor.name)).one()


