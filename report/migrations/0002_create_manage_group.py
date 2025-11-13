from django.db import migrations

def create_manage_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Permission = apps.get_model('auth', 'Permission')
    ContentType = apps.get_model('contenttypes', 'ContentType')

    # 1) Tạo (hoặc lấy) Group "manage"
    grp, _ = Group.objects.get_or_create(name='manage')

    # 2) Permission cho report: view_reports (tạo nếu chưa có)
    #    ContentType cho model ReportStub (app_label='report', model='reportstub')
    ct_report = ContentType.objects.filter(app_label='report', model='reportstub').first()
    if ct_report is None:
        # Phòng hờ: nếu vì lý do nào đó ContentType chưa có, tạo thủ công
        ct_report = ContentType.objects.create(app_label='report', model='reportstub')
    view_reports, _ = Permission.objects.get_or_create(
        content_type=ct_report,
        codename='view_reports',
        defaults={'name': 'Can view analytics reports'}
    )

    # 3) Permission xem CustomerInfo (userform.customerinfo)
    ct_customer = ContentType.objects.filter(app_label='userform', model='customerinfo').first()
    if ct_customer is not None:
        view_customer, _ = Permission.objects.get_or_create(
            content_type=ct_customer,
            codename='view_customerinfo',
            defaults={'name': 'Can view customer info'}
        )
        grp.permissions.add(view_customer)

    # Gắn luôn quyền report
    grp.permissions.add(view_reports)

def remove_manage_group(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name='manage').delete()

class Migration(migrations.Migration):
    dependencies = [
        ('report', '0001_initial'),
        ('userform', '0001_initial'),
        ('auth', '0012_alter_user_first_name_max_length'),
        ('contenttypes', '0002_remove_content_type_name'),
    ]
    operations = [
        migrations.RunPython(create_manage_group, remove_manage_group),
    ]
