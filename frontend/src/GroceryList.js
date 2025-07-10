import React from 'react';
import './GroceryList.css';

const GroceryList = ({ list }) => {
  if (!list || list.length === 0) {
    return null;
  }

  return (
    <div className="grocery-list-container">
      <h2>Your Grocery List</h2>
      <table className="grocery-list-table">
        <thead>
          <tr>
            <th>Item</th>
            <th>Quantity</th>
            <th>Price (USD)</th>
            <th>Store</th>
            <th>Protein</th>
            <th>Carbs</th>
            <th>Fats</th>
            <th>Calories</th>
            <th>Product Link</th>
          </tr>
        </thead>
        <tbody>
          {list.map((item, index) => (
            <tr key={index}>
              <td>{item.item}</td>
              <td>{item.quantity}</td>
              <td>${item.price_usd}</td>
              <td>{item.store}</td>
              <td>{item.protein}</td>
              <td>{item.carbs}</td>
              <td>{item.fats}</td>
              <td>{item.cals}</td>
              <td>
                {item.link ? (
                  <a href={item.link} target="_blank" rel="noopener noreferrer">
                    View Product
                  </a>
                ) : (
                  'N/A'
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

export default GroceryList;