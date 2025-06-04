from django.shortcuts import render
from django.contrib.auth.decorators import login_required
# Create your views here.

#@login_required
#def bienvenida(request):
 #   return render(request, 'bienvenida.html', {'usuario': request.user})
    #return render(request, 'bienvenida.html', {'empresa': request.empresa})

#@login_required
#def bienvenida(request):
 #   empresa = None
  #  if not request.user.is_superuser:
   #     empresa = request.user.perfilusuario.empresa
    #return render(request, 'bienvenida.html', {'empresa': empresa})

@login_required
def bienvenida(request):
    empresa = None
    if not request.user.is_superuser:
        empresa = request.user.perfilusuario.empresa
    return render(request, 'bienvenida.html', {
        'empresa': empresa,
    })
