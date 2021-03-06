# -*- coding: utf-8 -*-

import os
import json

from gluon.contrib.markdown import markdown2


### required - do no delete
def user(): return dict(form=auth())
def download(): return response.download(request,db)
def call(): return service()
### end requires


def index():
    return dict()


@auth.requires_login()
def codeeditor():
    """
    Shows a editor to view source files including their compiler errors and unit
    test results and to change source files directly in the browser.

    If not entry id is given the default solution.c file for the given task is
    shown. Otherwise the entry file is opened.

    /default/codeeditor/[task id]/[entry id] -> open an uploaded entry for a
                                                task in the code editor
    """
    # check if given arguments are valid
    if not request.args:
        raise HTTP(404, T('No task and entry id given!'))
    if len(request.args) > 2:
        raise HTTP(404, T('Too much arguments given!'))
    # check if argument is valid task number
    try:
        task_for_which_to_open_entry = int(request.args[0])
    except ValueError:
        raise HTTP(404, T('Invalid task id given.'))
    # check if entry id was given
    report_for_entry = ''
    if len(request.args) == 2:
        # get file path from entry
        try:
            entry_to_be_opened = int(request.args[1])
        except ValueError:
            raise HTTP(404, T('Invalid entry id given.'))
        row = db(db.Entries.id == entry_to_be_opened).select()
        if not row:
            raise HTTP(404, T('Invalid entry id given.'))
        code_file_path = row.first()['OnDiskPath']
        # get report for build of this entry
        row = db(db.Builds.Task == task_for_which_to_open_entry and
                 db.Builds.Entry == entry_to_be_opened).select()
        if row:
            if row.first()['Finished']:
                report_for_entry = row.first()['Report']
    else:
        # get file path from default file of task
        entry_to_be_opened = 0
        row = db(db.Tasks.id == task_for_which_to_open_entry).select()
        if not row:
            raise HTTP(404, T('Invalid task id given.'))
        task_data_path = row.first()['DataPath']
        # TODO Get code file name from tasks config.json file.
        code_file_path = os.path.join(task_data_path, 'src', 'solution.c')
    # open file and get content
    with open(code_file_path, 'r') as code_file:
        code = code_file.read()
    # prepare java script code for displaying the Ace editor (http://ace.c9.io/)
    js_on_submit_click = u"""
                         function on_submit()
                         {{
                             // send edited program to server as new entry
                             var editor = ace.edit("editor");
                             $.ajax({{
                                type: "POST",
                                url: "{upload_url}",
                                dataType: "application/json",
                                data: {{"filecontent": editor.getValue(),
                                        "requestFromCodeEditor": 1}},
                                complete: function(data) {{
                                    obj = JSON.parse(data.responseText);
                                    var entry_id = obj.new_id;
                                    build(entry_id)
                                }}
                             }});
                         }};
                         var intervalID = 0;
                         function build(entry_id)
                         {{
                             var buildNumber = 0;
                             // build newest entry for task
                             $.get("{build_url}/" + entry_id, "", function(data) {{
                                // call server to build newest entry
                                buildNumber = data.build_id;
                             }});
                             // wait for build status and redirect to editor for new entry
                             intervalID = setInterval(function() {{ reload(entry_id, buildNumber) }}, 2000);
                         }};
                         function reload(entry_id, buildNumber)
                         {{
                             $.get("{reload_url}/" + buildNumber, function(data) {{
                                 if (data.test_results != ""){{
                                     // clear timer and redirect
                                     clearInterval(intervalID);
                                     window.location.replace("{editor_url}/" + entry_id);
                                 }};
                             }});
                         }};
                         """.format(upload_url=URL(r=request, c='entry', f='add.json', args=(task_for_which_to_open_entry, )),
                                    build_url=URL(r=request, c='entry', f='build.json', args=(task_for_which_to_open_entry, )),
                                    reload_url=URL(r=request, c='entry', f='build_status.json'),
                                    editor_url=URL(r=request, c='default', f='codeeditor', args=(task_for_which_to_open_entry, )))
    editor_code = u"""
                  {on_submit}
                  // call function on click on submit button
                  $("#submit_button").bind('click', function () {{ on_submit() }} );
                  // setup Ace editor
                  var editor = ace.edit("editor");
                  editor.setTheme("ace/theme/monokai");
                  editor.getSession().setMode("ace/mode/c_cpp");
                  editor.session.setOption("useWorker", false);
                  var Range = ace.require('ace/range').Range;
                  // add markers for warnings and errors
                  """.format(on_submit=js_on_submit_click)#'alert("File saved!");'
    editor = DIV(code, _id='editor')
    # prepare javascript code for warnings and errors
    marker_js_code = ''
    if report_for_entry:
        report_data = json.loads(report_for_entry, encoding='utf-8')
        marker_js_code += build_annotations_for_errors(report_data)
    # add javascript blobs to page
    js1 = SCRIPT(_src=URL('static', 'js/src-noconflict/ace.js'), _type='text/javascript', _charset='utf-8')
    # TODO Fix problem with unicode characters in error descriptions!
    js2 = SCRIPT(u''.join([editor_code, marker_js_code]).encode('ascii', 'ignore'), _type='text/javascript', _charset='utf-8')
    submit_button = SPAN(INPUT(_type='button', _value=T('Save changes...'), _class='btn btn-primary', _id='submit_button'))
    # add test results
    if report_for_entry:
        test_results = build_test_results(report_data)
    else:
        test_results = ''
        if entry_to_be_opened:
            build_entry_link = A(T('Build entry'), _class='btn btn-primary',
                                 _href=URL(c='entry', f='build', args=(task_for_which_to_open_entry, entry_to_be_opened)))
            test_results = DIV(DIV(T('No unit tests results found!')), build_entry_link)
    # add task description
    task_from_db = db(db.Tasks.id == task_for_which_to_open_entry).select().first()
    task_description_path = os.path.join(task_from_db.DataPath, 'description.md')
    with open(task_description_path, 'r') as task_description_file:
        task_description = XML(markdown2.markdown(task_description_file.read()))
    return locals()


def build_test_results(report_data):
    if 'cunit' not in report_data or report_data['cunit']['returncode']:
        return DIV(T('Unit tests could not be executed!'))
    if 'tests' not in report_data['cunit']:
        return DIV(T('No unit tests results found!'))
    all_test_suites = []
    test_data = report_data['cunit']['tests']
    for suite in test_data:
        all_test_suites.append(H4('{}'.format(suite)))
        list_of_test_in_suite = []
        for test in test_data[suite]:
            icon_span_class = 'glyphicon ' + ('glyphicon-ok' if test_data[suite][test] else 'glyphicon-minus')
            icon_span = SPAN(_class=icon_span_class)
            label_span = SPAN('{}'.format(test), _class='test-result-label')
            list_element_class = 'list-group-item ' + ('list-group-item-success' if test_data[suite][test] else 'list-group-item-danger')
            current_test_list_element = LI(icon_span, label_span, _class=list_element_class)
            list_of_test_in_suite.append(current_test_list_element)
        all_test_suites.append(UL(*list_of_test_in_suite, _class='list-group checked-list-box'))
    return DIV(*all_test_suites)


def build_annotations_for_errors(report_data):
    """
    Build annotations and marker for code editor based on the build report. Data
    from build will be evaluated and all warnings and error by the compiler will
    be shown in the editor component.

    :param report_data: dictionary containing build data as returned by the
                        Celery worker and as stored in the database
                        (db.Builds.Report).
    :returns: string containing JavaScript code for annotations in code editor
    """
    from collections import namedtuple
    ConcernedLine = namedtuple('ConcernedLine', 'type desc')
    list_of_concerned_lines = {}
    for message in report_data['gcc']['messages']:
        # generate message type
        if message['type'] == 'warning':
            message_type = 'warning'
        elif message['type'] == 'error':
            message_type = 'error'
        else:
            message_type = ''
        # parse and adjust line number
        try:
            # minus one because indexes for code editor begin with zero!
            line_with_error = str(int(message['line']) - 1)
        except (ValueError, TypeError):
            line_with_error = -1
        # add or replace line data in list
        if line_with_error in list_of_concerned_lines:
            old_line_data = list_of_concerned_lines[line_with_error]
            # only overwrite message type if not already highest message level ('error')
            new_line_data = ConcernedLine(type=message_type if old_line_data.type != 'error' else old_line_data.type,
                                          desc='\\n'.join((old_line_data.desc, message['desc'])))
            list_of_concerned_lines[line_with_error] = new_line_data
        else:
            list_of_concerned_lines[line_with_error] = ConcernedLine(message_type, message['desc'])
    # build JavaScript code for annotations
    js_code = ''
    annotations = ''
    for line_with_error, line_data in list_of_concerned_lines.items():
        # 'line' instead of 'text' as parameter of addMarker() function highlights the whole line
        js_code += u"""editor.getSession().addMarker(new Range({line}, 0, {line}, 100), "{type}", "text");
                    """.format(type=line_data.type, line=line_with_error)
        # add annotation icons for lines with warnings or errors
        # types of annotations for Ace code editor: warning, error, information
        annotations += u"""{{row: {line}, column: 1, text: "{desc}", type: "{type}"}},
                        """.format(type=line_data.type, desc=line_data.desc, line=line_with_error)
    js_code += u'editor.getSession().setAnnotations([{}]);'.format(annotations)
    return js_code


@auth.requires_login()
def view_result():
    import os
    # TODO Check if syntac highlighting should be done on server side or on the client
    # See: http://alexgorbatchev.com/SyntaxHighlighter/
    from pygments import highlight
    from pygments.lexers import PythonLexer
    from pygments.formatters import HtmlFormatter

    # get source and highlight it
    source_file = os.path.join(request.folder, 'private', 'main.c')
    # create highlighted source and wrap it into XML object to prevent
    # characters like < or > to be escaped into HTML entities
    code = XML(highlight(open(source_file, 'rb').read(), PythonLexer(),
                         HtmlFormatter(linenos='inline', lineanchors='lineanchor', linespans='line')))

    # highlight all errors in source and show mouse over info box
    errors = ( (2, 'Can not import file.'), (17, 'Function main not ok.'), (22, 'Do not know any more errors.') )
    commands = ''
    styles = ''
    # TODO: Write my own HTML formatter for pygments to include error and warning classes into HTML
    for error in errors:
        commands += "$('span#line-{lineno}').attr('title','{message}');".format(lineno=error[0], message=error[1])
        styles += '#line-{lineno} {{ background-color: yellow }}'.format(lineno=error[0])
    javascript = SCRIPT(commands, _type='text/javascript')
    error_styles = STYLE(XML(styles))

    return dict(code=code, javascript=javascript, error_styles=error_styles)


def error():
    return dict()
