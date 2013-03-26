# -*- coding: UTF-8 -*-

from flask import (request, abort, redirect, url_for, render_template, json,
                   flash)
from flask.ext.login import current_user
from wtforms import Form, HiddenField, TextField, BooleanField, \
    IntegerField, validators
from lite_mms.portal.manufacture import manufacture_page
import lite_mms.constants as constants
from lite_mms.utilities import decorators, Pagination
from lite_mms.permissions.work_command import view_work_command


@manufacture_page.route("/")
def index():
    return redirect(url_for("manufacture.work_command_list"))


@manufacture_page.route("/work-command-list", methods=["POST", "GET"])
@decorators.templated("/manufacture/work-command-list.html")
@decorators.nav_bar_set
def work_command_list():
    decorators.permission_required(view_work_command)
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', 1, type=int)
    harbor = request.args.get('harbor', u"全部")
    order_id = request.args.get('order_id', None)
    status_list = []
    schedule_button = False
    retrieve_button = False
    if status == constants.work_command.STATUS_DISPATCHING:
        status_list.extend(
            [constants.work_command.STATUS_REFUSED])
        schedule_button = True
    elif status == constants.work_command.STATUS_ENDING:
        status_list.extend(
            [constants.work_command.STATUS_LOCKED,
             constants.work_command.STATUS_ASSIGNING])
        retrieve_button = True
    status_list.append(status)
    import lite_mms.apis as apis

    work_commands, total_cnt = apis.manufacture.get_work_command_list(
        status_list=status_list, harbor=harbor, order_id=order_id,
        start=(page - 1) * constants.UNLOAD_SESSION_PER_PAGE,
        cnt=constants.UNLOAD_SESSION_PER_PAGE)
    pagination = Pagination(page, constants.UNLOAD_SESSION_PER_PAGE, total_cnt)
    param_dic = {'titlename': u'工单列表', 'pagination': pagination,
                 'status': status, 'work_command_list': work_commands,
                 'harbor': harbor, 'schedule': schedule_button,
                 'retrieve': retrieve_button,
                 'status_list': apis.manufacture.get_status_list(),
                 'harbor_list': apis.harbor.get_harbor_list(),
                 'all_status': dict(
                     [(name, getattr(constants.work_command, name)) for name in
                      constants.work_command.__dict__ if
                      name.startswith("STATUS")]),
    }
    return param_dic


@manufacture_page.route("/work-command/<id_>")
@decorators.templated("/manufacture/work-command.html")
@decorators.nav_bar_set
def work_command(id_):
    decorators.permission_required(view_work_command)
    import lite_mms.apis as apis

    wc = apis.manufacture.get_work_command(id_)
    if not wc:
        abort(404)
    return {"work_command": wc,
            "backref": request.args.get("backref")}


@manufacture_page.route('/schedule', methods=['GET', 'POST'])
@decorators.nav_bar_set
def schedule():
    import lite_mms.apis as apis

    if request.method == 'GET':
        decorators.permission_required(view_work_command)

        def _wrapper(department):
            return dict(id=department.id, name=department.name,
                        procedure_list=[dict(id=p.id, name=p.name) for p in
                                        department.procedure_list])

        work_command_id_list = request.args.getlist("work_command_id")
        pre_url = request.args.get(
            'purl', url_for('manufacture.work_command_list'))
        department_list = apis.manufacture.get_department_list()
        from lite_mms.basemain import nav_bar

        if 1 == len(work_command_id_list):
            work_command = apis.manufacture.get_work_command(
                work_command_id_list[0])
            # TODO if work_command is not the first work command, then
            # harbor may not be the sub_order's harbor
            default_department_id = apis.harbor.get_harbor_model(
                work_command.harbor.name).department.id
            return render_template("/manufacture/schedule-work-command.html",
                                   **{'titlename': u'排产',
                                      'department_list': [_wrapper(d) for d in
                                                          department_list],
                                      'work_command': work_command,
                                      'purl': pre_url,
                                      'default_department_id':
                                          default_department_id,
                                      'nav_bar': nav_bar
                                   })
        else:
            work_command_list = [apis.manufacture.get_work_command(id)
                                 for id in work_command_id_list]
            default_department_id = None
            department_dict = {}
            department_set = set()
            # TODO 这个太复杂了，显然这里需要替换为WorkCommand数据库对象
            for work_command in work_command_list:
                for d in department_list:
                    # TODO if work_command is not the first, then its harbor
                    # may not be the same with sub order's
                    if work_command.harbor in d.harbor_list:
                        department_set.add(d.id)
                        department_dict.setdefault(work_command.id,
                                                   dict(id=d.id, name=d.name))
            if len(department_set) == 1: # 所有的工单都来自于同一个车间
                default_department_id = department_set.pop()

            total_weight = sum(work_command.org_weight for work_command in [
                apis.manufacture.get_work_command(id) for id in
                work_command_id_list])
            param_dic = {'titlename': u'批量排产',
                         'department_list': [_wrapper(d) for d in
                                             department_list],
                         'purl': pre_url,
                         'weight': total_weight,
                         'work_command_list': work_command_list,
                         'default_department_dict': json.dumps(
                             department_dict),
                         'default_department_id': default_department_id,
                         'nav_bar': nav_bar
            }
            return render_template("/manufacture/batch-schedule.html",
                                   **param_dic)
    else: # POST
        from lite_mms.permissions.work_command import schedule_work_command

        decorators.permission_required(schedule_work_command, ("POST",))
        form = WorkCommandForm(request.form)
        if form.validate():
            department = apis.manufacture.get_department(
                form.department_id.data)
            if not department:
                abort(403)
            work_command_id_list = form.id.raw_data
            for work_command_id in work_command_id_list:
                work_command = apis.manufacture.get_work_command(
                    int(work_command_id))

                if work_command:
                    d = dict(tech_req=form.tech_req.data,
                             urgent=form.urgent.data,
                             department_id=department.id,
                    )
                    if form.procedure_id.data:
                        d.update(procedure_id=form.procedure_id.data)

                    work_command.go(actor_id=current_user.id,
                                    action=constants.work_command.ACT_DISPATCH,
                                    **d)
                else:
                    abort(403)
            flash(u"工单(%s)已经被成功排产至车间(%s)" %
                  (",".join(work_command_id_list), department.name))
            return redirect(form.purl.data if form.purl.data else url_for(
                "manufacture.work_command_list"))
        else:
            return render_template("result.html", error_content=form.errors)

# TODO does POST needed?
@manufacture_page.route('/retrieve', methods=['POST'])
def retrieve():
    import lite_mms.apis as apis

    work_command_id_list = request.form.getlist('work_command_id',
                                                type=int)
    import urllib2

    pre_url = urllib2.unquote(request.form.get('purl',
                                               url_for(
                                                   'manufacture'
                                                   '.work_command_list')))
    for id in work_command_id_list:
        try:
            apis.manufacture.WorkCommandWrapper.get_work_command(id).go(
                actor_id=current_user.id,
                action=constants.work_command.ACT_RETRIEVAL)
        except ValueError as e:
            return e.message, 403
        except AttributeError:
            abort(404)
    flash(u"回收成功")
    return redirect(pre_url)


@manufacture_page.route('/qir-work-command-list')
@decorators.templated('/manufacture/quality-inspection-work-command-list.html')
@decorators.nav_bar_set
def QI_work_command_list():
    page = request.args.get('page', 1, type=int)
    department_id = request.args.get('department', type=int)
    from lite_mms import apis

    work_command_list, total_cnt = apis.manufacture.get_work_command_list(
        status_list=[constants.work_command.STATUS_FINISHED],
        department_id=department_id, normal=True)
    pagination = Pagination(page, constants.UNLOAD_SESSION_PER_PAGE, total_cnt)
    return {'titlename': u'工单列表', 'work_command_list': work_command_list,
            'pagination': pagination, 'department': department_id,
            'department_list': apis.manufacture.get_department_list()
    }


@manufacture_page.route('/qir-list')
@decorators.templated('/manufacture/quality-inspection-report-list.html')
@decorators.nav_bar_set
def QI_report_list():
    work_command_id = request.args.get("id", type=int)
    if work_command_id:
        from lite_mms import apis

        work_command = apis.manufacture.get_work_command(work_command_id)
        qir_list, total_cnt = apis.quality_inspection.get_qir_list(
            work_command_id)
        return {'titlename': u'质检单', 'qir_list': qir_list,
                'work_command': work_command,
                'qir_result_list': apis.quality_inspection.get_QI_result_list()}
    else:
        abort(403)


class WorkCommandForm(Form):
    id = HiddenField('id', [validators.required()])
    purl = HiddenField('purl')
    procedure_id = IntegerField('procedure_id')
    department_id = IntegerField('department_id', [validators.required()])
    tech_req = TextField('tech_req')
    urgent = BooleanField('urgent')
