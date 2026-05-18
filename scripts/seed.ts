/**
 * Seed script — populates Cars and Services for local development.
 * Run: npx tsx scripts/seed.ts
 */
import { db, carsTable, servicesTable } from "../lib/db/src/index";

const cars = [
  { brand: "Toyota",    model: "Camry",   year: 2019 },
  { brand: "Kia",       model: "Rio",     year: 2021 },
  { brand: "Hyundai",   model: "Solaris", year: 2020 },
  { brand: "Lada",      model: "Vesta",   year: 2022 },
  { brand: "Volkswagen",model: "Polo",    year: 2018 },
];

const services = [
  {
    name: "Замена тормозных колодок",
    price: "3500.00",
    duration: 60,
    target_tags: ["тормоза", "тормозной", "колодки", "скрипит", "скрип"],
  },
  {
    name: "Диагностика подвески",
    price: "1500.00",
    duration: 45,
    target_tags: ["подвеска", "стук", "стучит", "удар", "яма", "амортизатор"],
  },
  {
    name: "Замена масла и фильтра",
    price: "2200.00",
    duration: 30,
    target_tags: ["масло", "замена масла", "фильтр", "течь", "уровень"],
  },
  {
    name: "Диагностика двигателя",
    price: "2000.00",
    duration: 60,
    target_tags: ["двигатель", "мотор", "троит", "вибрация", "запуск", "не заводится"],
  },
  {
    name: "Замена ремня ГРМ",
    price: "8500.00",
    duration: 180,
    target_tags: ["ремень", "грм", "свист", "скрежет"],
  },
  {
    name: "Шиномонтаж (4 колеса)",
    price: "1200.00",
    duration: 40,
    target_tags: ["шины", "колёса", "резина", "давление", "прокол", "замена шин"],
  },
  {
    name: "Замена аккумулятора",
    price: "4500.00",
    duration: 20,
    target_tags: ["аккумулятор", "батарея", "не заряжается", "разряд", "стартер"],
  },
  {
    name: "Ремонт рулевой рейки",
    price: "12000.00",
    duration: 240,
    target_tags: ["руль", "рулевая", "рейка", "люфт", "тяжело"],
  },
];

async function seed() {
  console.log("Seeding cars...");
  const insertedCars = await db
    .insert(carsTable)
    .values(cars)
    .onConflictDoNothing()
    .returning({ id: carsTable.id, brand: carsTable.brand, model: carsTable.model });
  console.log(`  Inserted ${insertedCars.length} cars`);

  console.log("Seeding services...");
  const insertedServices = await db
    .insert(servicesTable)
    .values(services)
    .onConflictDoNothing()
    .returning({ id: servicesTable.id, name: servicesTable.name });
  console.log(`  Inserted ${insertedServices.length} services`);

  console.log("Seed complete.");
  process.exit(0);
}

seed().catch((err) => {
  console.error("Seed failed:", err);
  process.exit(1);
});
