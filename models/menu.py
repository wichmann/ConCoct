# -*- coding: utf-8 -*-

response.title = settings.title
response.subtitle = settings.subtitle
response.meta.author = '%(author)s <%(author_email)s>' % settings
response.meta.keywords = settings.keywords
response.meta.description = settings.description

#response.logo = IMG(_class='img-rounded', _src=URL('static', 'images/logo.png'), _height='50px')
response.logo = A('ConCoct', _class="navbar-brand", _href=URL('default', 'index'))

response.menu = []
if auth.is_logged_in():
    # visible for all registered users
    response.menu.append((T('Show tasks'),URL('task','list')==URL(),URL('task','list'),[]))
    #response.menu.append((T('Add entry'),URL('entry','add')==URL(),URL('entry','add'),[]))
    response.menu.append((T('List entries'),URL('entry','add')==URL(),URL('entry','list'),[]))
    #response.menu.append((T('Code editor'),URL('default','codeeditor')==URL(),URL('default','codeeditor'),[]))
    if auth.has_membership('teacher'):
        # only for teachers
        response.menu.append((T('Add tasks'),URL('task','add')==URL(),URL('task','add'),[]))
