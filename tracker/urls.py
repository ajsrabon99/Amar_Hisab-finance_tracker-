from django.urls import path
from . import views

app_name = "tracker"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("yearly/", views.yearly_overview, name="yearly_overview"),
    path("add/", views.add_transaction, name="add_transaction"),
    path("transfer/", views.transfer_money, name="transfer_money"),
    path("transactions/", views.transactions, name="transactions"),
    path("transactions/<int:pk>/delete/", views.delete_transaction, name="delete_transaction"),
    path("export/csv/", views.export_csv, name="export_csv"),
    path('verify-email/', views.verify_email, name='verify_email'),
    path('resend-code/', views.resend_code, name='resend_code'),
    path('signup/', views.custom_signup, name='custom_signup'),  
    path("profile/", views.profile, name="profile"),
]
