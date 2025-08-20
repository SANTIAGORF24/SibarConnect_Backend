#!/usr/bin/env python3

try:
    print("Probando importaciones...")
    
    from app.api.routes.chats.ai import router
    print("✅ Router de IA importado correctamente")
    
    print("Rutas disponibles:")
    for route in router.routes:
        if hasattr(route, 'path'):
            print(f"  {route.methods} {route.path}")
        else:
            print(f"  {type(route)}")
            
except Exception as e:
    print(f"❌ Error importando: {e}")
    import traceback
    traceback.print_exc()
