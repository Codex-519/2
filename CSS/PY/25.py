a=int(input("Enter the price of product1 : "))
b=int(input("Enter the price of product2 : "))
c=int(input("Enter the price of product3 : "))
total=a+b+c
if total>=1000:
    discount=total*0.1
    total=total-discount
    print("Total price after discount:",total)
else:
    print("Total price:",total)