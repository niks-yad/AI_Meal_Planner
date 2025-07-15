'use client';

import React from 'react';

interface GroceryItem {
  item: string;
  quantity: string;
  category: string;
  link: string | null;
  protein: string | null;
  carbs: string | null;
  fats: string | null;
  cals: string | null;
}

interface GroceryListProps {
  list: GroceryItem[];
}

const GroceryList: React.FC<GroceryListProps> = ({ list }) => {
  // Use mock data if no list is provided or list is empty
  const displayList = list ;

  // Group items by category
  const groupedList = displayList.reduce((acc, item) => {
    (acc[item.category] = acc[item.category] || []).push(item);
    return acc;
  }, {} as Record<string, GroceryItem[]>);


  return (
    <div className="bg-white p-6 rounded-lg shadow-md w-full max-w-2xl mx-auto mt-8">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 text-center">Your Grocery List</h2>
      
      {Object.entries(groupedList).map(([category, items]) => (
        <div key={category} className="mb-6">
          <h3 className="text-xl font-semibold mb-3 text-gray-700 border-b pb-2">{category}</h3>
          <ul className="space-y-2">
            {items.map((item, index) => (
              <li key={index} className="bg-gray-50 p-3 rounded-md flex justify-between items-center">
                <div>
                  <p className="font-medium text-gray-800">{item.item} - {item.quantity}</p>
                  <p className="text-sm text-gray-500">
                    Protein: {item.protein} | Carbs: {item.carbs} | Fats: {item.fats} | Cals: {item.cals}
                  </p>
                  {item.link && (
                    <a 
                      href={item.link} 
                      target="_blank" 
                      rel="noopener noreferrer" 
                      className="text-blue-500 hover:underline text-sm"
                    >
                      View Product
                    </a>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      ))}
    </div>
  );
};

export default GroceryList;
