num=int(input("Enter a three digit number : "))
sum=num%10
num=num//10
sum=sum+num%10
num=num//10
sum=sum+num%10
print("Sum of digits:",sum)