from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(value, arg):
    attrs = {}
    classes = arg.split(' ')
    
    if 'class' in value.field.widget.attrs:
        classes.insert(0, value.field.widget.attrs['class'])
    
    attrs['class'] = ' '.join(classes)
    return value.as_widget(attrs=attrs)