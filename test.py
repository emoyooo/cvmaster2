from utils.db import get_normalized_metrics

# Тестовый код (возьмем медсестру из твоего примера, там много данных во всех таблицах)
TEST_CODE = "29-1141.01" 

# Список таблиц, которые мы нормализовали
TABLES = [
    "skills", 
    "knowledge", 
    "abilities", 
    "work_styles", 
    "work_activities"
]

def test_full_normalization():
    print(f"--- 🛡️ СТАРТ ПОЛНОГО ТЕСТА НОРМАЛИЗАЦИИ ДАННЫХ ---")
    print(f"O*NET Код: {TEST_CODE}\n")

    for table in TABLES:
        print(f"📊 Таблица: {table.upper()}")
        try:
            data = get_normalized_metrics(table, TEST_CODE)
            
            if not data:
                print(f"   ⚠️ Данных нет (возможно, этот код не представлен в этой таблице)")
                continue

            # Выводим первые 2 записи для примера
            for row in data[:2]:
                name = row.get('Element Name', 'N/A')
                scale = row.get('Scale ID', 'N/A')
                raw = row.get('Data Value', 'N/A')
                norm = row.get('normalized_score', 'N/A')
                
                print(f"   🔹 {name} | {scale} | Raw: {raw} -> {norm}%")
            
            print(f"   ✅ Всего обработано строк: {len(data)}\n")

        except Exception as e:
            print(f"   ❌ Ошибка в таблице {table}: {e}\n")

    print(f"--- 🏁 ТЕСТ ЗАВЕРШЕН ---")

if __name__ == "__main__":
    test_full_normalization()