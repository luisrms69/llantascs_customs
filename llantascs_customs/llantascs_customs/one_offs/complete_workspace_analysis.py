import frappe
import json
from frappe.utils import now

def run():
    """
    Análisis COMPLETO de TODOS los campos del Workspace - no solo Dashboard Chart
    """
    print("=== ANÁLISIS COMPLETO DE WORKSPACE ===")
    print(f"Timestamp: {now()}")
    print()
    
    workspace_name = "Vendedores"
    
    try:
        # Obtener el documento completo del workspace
        workspace = frappe.get_doc("Workspace", workspace_name)
        
        print(f"📋 WORKSPACE: {workspace_name}")
        print("=" * 60)
        
        # TODOS LOS CAMPOS PRINCIPALES DEL WORKSPACE
        main_fields = [
            'name', 'title', 'label', 'public', 'is_default', 'sequence_id',
            'for_user', 'parent_page', 'module', 'icon', 'indicator_color', 
            'restrict_to_domain', 'hide_custom', 'is_hidden', 'content',
            'creation', 'modified', 'modified_by', 'owner', 'docstatus', 'idx'
        ]
        
        print("📊 CAMPOS PRINCIPALES DEL WORKSPACE:")
        for field in main_fields:
            if hasattr(workspace, field):
                value = getattr(workspace, field)
                if field == 'content' and value:
                    # Mostrar content parseado si es JSON válido
                    try:
                        content_parsed = json.loads(value)
                        print(f"  - {field}: JSON con {len(content_parsed)} bloques")
                    except:
                        print(f"  - {field}: {len(str(value))} caracteres")
                else:
                    print(f"  - {field}: {repr(value)}")
            else:
                print(f"  - {field}: ❌ NO EXISTE")
        
        print()
        
        # TODAS LAS TABLAS HIJO DEL WORKSPACE
        child_tables = {
            'number_cards': 'Number Cards',
            'charts': 'Charts', 
            'shortcuts': 'Shortcuts',
            'links': 'Links',
            'quick_lists': 'Quick Lists',
            'custom_blocks': 'Custom Blocks',
            'roles': 'Roles'
        }
        
        print("📊 TABLAS HIJO DEL WORKSPACE:")
        for table_field, table_name in child_tables.items():
            if hasattr(workspace, table_field):
                child_records = getattr(workspace, table_field)
                print(f"\n  🔸 {table_name} ({table_field}):")
                print(f"    - Cantidad de registros: {len(child_records)}")
                
                # Mostrar detalles de cada registro hijo
                for idx, record in enumerate(child_records, 1):
                    print(f"    - Registro {idx}:")
                    # Obtener todos los campos del registro hijo
                    for key, value in record.as_dict().items():
                        if key not in ['name', 'owner', 'creation', 'modified', 'modified_by', 'docstatus']:
                            print(f"      {key}: {repr(value)}")
            else:
                print(f"  🔸 {table_name}: ❌ NO EXISTE")
        
        print()
        
        # CONTENT PARSEADO (si es JSON)
        if workspace.content:
            try:
                content_data = json.loads(workspace.content)
                print("📊 CONTENT BLOCKS PARSEADOS:")
                for idx, block in enumerate(content_data, 1):
                    print(f"  Block {idx}:")
                    print(f"    - id: {block.get('id', 'N/A')}")
                    print(f"    - type: {block.get('type', 'N/A')}")
                    print(f"    - data: {block.get('data', 'N/A')}")
                    if block.get('data') and isinstance(block.get('data'), dict):
                        for data_key, data_value in block['data'].items():
                            print(f"      {data_key}: {repr(data_value)}")
            except Exception as e:
                print(f"❌ Error parseando content: {e}")
        
        print()
        
        # META INFORMACIÓN DEL DOCTYPE WORKSPACE
        workspace_meta = frappe.get_meta("Workspace")
        print("📊 METADATA DEL DOCTYPE WORKSPACE:")
        print(f"  - Total de campos: {len(workspace_meta.fields)}")
        print("  - Campos disponibles:")
        for field in workspace_meta.fields:
            if field.fieldname:
                print(f"    • {field.fieldname}: {field.label or 'Sin Label'} ({field.fieldtype})")
        
    except Exception as e:
        print(f"❌ Error en análisis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    run()