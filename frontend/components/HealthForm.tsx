'use client';

import React from 'react';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';

// Define the schema for health data using Zod
const healthDataSchema = z.object({
  heightFeet: z.coerce.number().min(1, "Height (feet) is required").max(8, "Height (feet) seems too high"),
  heightInches: z.coerce.number().min(0, "Height (inches) cannot be negative").max(11, "Height (inches) must be less than 12"),
  weight: z.coerce.number().min(50, "Weight is required").max(1000, "Weight seems too high"),
  activityLevel: z.enum(["sedentary", "lightly_active", "moderately_active", "very_active", "extra_active"]),
});

type HealthDataFormInputs = z.infer<typeof healthDataSchema>;

interface HealthFormProps {
  onSubmit: (data: HealthDataFormInputs) => void;
  isLoading: boolean;
}

const HealthForm: React.FC<HealthFormProps> = ({ onSubmit, isLoading }) => {
  const { register, handleSubmit, formState: { errors } } = useForm<HealthDataFormInputs>({
    resolver: zodResolver(healthDataSchema),
    defaultValues: {
      heightFeet: 5,
      heightInches: 9,
      weight: 150,
      activityLevel: 'sedentary',
    },
  });

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="bg-white p-6 rounded-lg shadow-md w-full max-w-md mx-auto">
      <h2 className="text-2xl font-bold mb-6 text-gray-800 text-center">Your Health Profile</h2>
      
      <div className="mb-4">
        <label htmlFor="heightFeet" className="block text-gray-700 text-sm font-bold mb-2">Height</label>
        <div className="flex space-x-2">
          <input
            type="number"
            id="heightFeet"
            {...register('heightFeet')}
            placeholder="Feet"
            className="shadow appearance-none border rounded w-1/2 py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          />
          <input
            type="number"
            id="heightInches"
            {...register('heightInches')}
            placeholder="Inches"
            className="shadow appearance-none border rounded w-1/2 py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
          />
        </div>
        {errors.heightFeet && <p className="text-red-500 text-xs italic mt-1">{errors.heightFeet.message}</p>}
        {errors.heightInches && <p className="text-red-500 text-xs italic mt-1">{errors.heightInches.message}</p>}
      </div>

      <div className="mb-4">
        <label htmlFor="weight" className="block text-gray-700 text-sm font-bold mb-2">Weight (lbs)</label>
        <input
          type="number"
          id="weight"
          {...register('weight')}
          placeholder="Pounds"
          className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
        />
        {errors.weight && <p className="text-red-500 text-xs italic mt-1">{errors.weight.message}</p>}
      </div>

      <div className="mb-6">
        <label htmlFor="activityLevel" className="block text-gray-700 text-sm font-bold mb-2">Activity Level</label>
        <select
          id="activityLevel"
          {...register('activityLevel')}
          className="block appearance-none w-full bg-white border border-gray-400 hover:border-gray-500 px-4 py-2 pr-8 rounded shadow leading-tight focus:outline-none focus:shadow-outline"
        >
          <option value="sedentary">Sedentary</option>
          <option value="lightly_active">Lightly Active</option>
          <option value="moderately_active">Moderately Active</option>
          <option value="very_active">Very Active</option>
          <option value="extra_active">Extra Active</option>
        </select>
        {errors.activityLevel && <p className="text-red-500 text-xs italic mt-1">{errors.activityLevel.message}</p>}
      </div>

      <div className="flex items-center justify-center">
        <button
          type="submit"
          disabled={isLoading}
          className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {isLoading ? 'Generating...' : 'Generate Meal Plan'}
        </button>
      </div>
    </form>
  );
};

export default HealthForm;
