from django import forms

class PlaceholderSelect(forms.Select):
        
    def __init__(self, attrs=None, choices=()):
        base = {'class': 'form-select placeholder-light'}  # 👈 form-select
        if attrs:
            base.update(attrs)
        super().__init__(attrs=base, choices=choices)
    
    def create_option(self, name, value, label, selected, index, subindex=None, attrs=None):
        
        option = super().create_option(name, value, label, selected, index,
                                    subindex=subindex, attrs=attrs)
        if value in (None, ''):
            option['attrs']['disabled'] = True
            option['attrs']['hidden'] = True
            option['attrs']['selected'] = True
            
        return option