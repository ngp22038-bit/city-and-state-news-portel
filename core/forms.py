from django import forms
from .models import User

class SignupForm(forms.ModelForm):
    password1 = forms.CharField(label='Password', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Re-Password', widget=forms.PasswordInput)
    role = forms.ChoiceField(
        choices=[('', 'Select Role'), ('owner', 'Reporter'), ('user', 'Reader')],
        initial='',
    )

    class Meta:
        model = User
        fields = ['first_name','last_name','gender','role','mobile','email']
        widgets = {
            'gender': forms.RadioSelect(),
        }

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password1")
        confirm_password = cleaned_data.get("password2")

        if password and confirm_password and password != confirm_password:
            self.add_error('password2', "Passwords do not match.")

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password1'])
        if commit:
            user.save()
        return user

class LoginForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)