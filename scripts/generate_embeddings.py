import time
from utils.db import supabase
from utils.ai import generate_embedding

def fill_occupations():
    print("🚀 Векторизация таблицы occupations...")
    
    # Чтобы Postgres не ругался на звездочку, берем название в двойные кавычки: '"O*NET-SOC Code"'
    try:
        res = supabase.table("occupations").select('"O*NET-SOC Code", "Title", "Description"').is_("embedding", "null").execute()
        rows = res.data
    except Exception as e:
        print(f"❌ Ошибка при чтении: {e}")
        return

    if not rows:
        print("✅ Всё уже заполнено!")
        return

    print(f"Найдено строк: {len(rows)}")

    for i, row in enumerate(rows):
        # В объекте row ключ будет называться без кавычек: 'O*NET-SOC Code'
        text = f"{row['Title']}: {row['Description']}"
        try:
            vector = generate_embedding(text)
            
            # В фильтре .eq() название колонки СНОВА берем в двойные кавычки
            supabase.table("occupations")\
                .update({"embedding": vector})\
                .eq('"O*NET-SOC Code"', row["O*NET-SOC Code"])\
                .execute()
                
            if i % 20 == 0: 
                print(f"Готово {i}/{len(rows)}...")
        except Exception as e:
            print(f"❌ Ошибка в строке {row.get('O*NET-SOC Code')}: {e}")
            time.sleep(2)

if __name__ == "__main__":
    fill_occupations()