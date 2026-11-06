const express = require('express');
const router = express.Router();

router.post('/create-order', async (req, res) => {
  try {
    const { amount, currency = 'INR' } = req.body;
    if (!amount) {
      return res.status(400).json({ message: 'Amount is required' });
    }

    res.json({
      success: true,
      message: 'Razorpay-ready order payload generated.',
      order: {
        amount: Number(amount),
        currency,
        key: process.env.RAZORPAY_KEY_ID || 'rzp_test_placeholder',
      },
    });
  } catch (error) {
    res.status(500).json({ message: 'Payment setup failed', error: error.message });
  }
});

module.exports = router;
