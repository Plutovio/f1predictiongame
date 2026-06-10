from django.db import migrations

def cleanup_stale_drivers(apps, schema_editor):
    Driver = apps.get_model('core', 'Driver')
    DriverTeamHistory = apps.get_model('core', 'DriverTeamHistory')
    
    # 1. Delete the unwanted drivers
    stale_abbrs = ['DOO', 'TSU', 'POU']
    deleted_drivers, _ = Driver.objects.filter(abbreviation__in=stale_abbrs).delete()
    
    # 2. Delete incorrect driver team histories
    # LAW (Liam Lawson) -> Red Bull Racing (red_bull) is incorrect
    h1, _ = DriverTeamHistory.objects.filter(
        driver__abbreviation='LAW',
        team__constructor_id='red_bull'
    ).delete()
    
    # HAD (Isack Hadjar) -> Racing Bulls (rb) is incorrect
    h2, _ = DriverTeamHistory.objects.filter(
        driver__abbreviation='HAD',
        team__constructor_id='rb'
    ).delete()

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_alter_prediction_session_type_and_more'),
    ]

    operations = [
        migrations.RunPython(cleanup_stale_drivers),
    ]
