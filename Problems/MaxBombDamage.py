# You are given an m by m matrix with 1s and 0s.
# 1 means building and 0 means open space.
# You are given a bomb of radius r and you need to find the max number of buildings that will be destroyed and where to place the bomb.
# consider building is destroyed even if more than half of it is destroyed
# Write a function that takes the matrix and radius as input and returns the max number of buildings destroyed and the location of the bomb.
# Follow PEP8 standards
# Time complexity: O(m^2)
# Space complexity: O(1)
#
# Example:
# Input:
# 1 0 0 0 0
# 1 1 1 0 0
# 1 0 0 0 0
# 1 0 0 0 0
# 1 0 0 0 0
# radius = 1
# Output:
# 3, (1, 1)

def max_building_damage(matrix, radius):
    max_damage = 0
    bomb_location = (0, 0)
    for i in range(len(matrix)):
        for j in range(len(matrix[0])):
            damage = 0
            for k in range(i - radius, i + radius + 1):
                for l in range(j - radius, j + radius + 1):
                    if k < 0 or k >= len(matrix) or l < 0 or l >= len(matrix[0]):
                        continue
                    if matrix[k][l] == 1:
                        damage += 1
            if damage > max_damage:
                max_damage = damage
                bomb_location = (i, j)
    return max_damage, bomb_location
# compute time complexity for this function
# compute space complexity for this function
# write tests for this function
# write a main function that calls this function with different inputs
# and prints the output
# run the main function


matrix = [[1, 0, 0, 0, 0],
            [1, 1, 1, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 0, 0, 0, 0],
            [1, 0, 0, 0, 0]]

radius = 3
print(max_building_damage(matrix, radius))



