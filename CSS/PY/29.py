even_sum=0
odd_sum=0
for i in range(1,11):
    if i%2==0:
        even_sum=even_sum+i
    else:
        odd_sum=odd_sum+i
print(f"Even Sum = {even_sum}")
print(f"Odd Sum = {odd_sum}")