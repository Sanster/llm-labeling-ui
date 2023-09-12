module.exports = {
  i18n: {
    defaultLocale: 'en',
    locales: [],
  },
  localePath:
    typeof window === 'undefined'
      ? require('path').resolve('./public/locales')
      : '/public/locales',
};
