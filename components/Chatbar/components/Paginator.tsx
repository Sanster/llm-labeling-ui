import { useContext } from 'react';

import HomeContext from '@/utils/home.context';

// 怎么添加新的状态？把 messages 部分换成从 server 端读取
export const Paginator = () => {
  const {
    state: { totalPages, page, totalConversations },
    dispatch: homeDispatch,
  } = useContext(HomeContext);

  const handlePrevClick = () => {
    if (page > 0) {
      homeDispatch({
        field: 'page',
        value: page - 1,
      });
    } else if (page === 0) {
      homeDispatch({
        field: 'page',
        value: totalPages - 1,
      });
    }
  };

  const handleNextClick = () => {
    if (page < totalPages - 1) {
      homeDispatch({
        field: 'page',
        value: page + 1,
      });
    } else if (page === totalPages - 1) {
      homeDispatch({
        field: 'page',
        value: 0,
      });
    }
  };

  return (
    <div className="flex w-full flex-col gap-1">
      <div className="flex flex-row w-full items-center justify-between">
        <button
          className="text-sidebar py-1 w-[60px] flex-shrink-0 cursor-pointer select-none items-center rounded-md border border-white/20 text-white transition-colors duration-200 hover:bg-gray-500/10"
          onClick={handlePrevClick}
        >
          Prev
        </button>
        {page + 1}/{totalPages} ({totalConversations})
        <button
          className="text-sidebar py-1 w-[60px] flex-shrink-0 cursor-pointer select-none items-center rounded-md border border-white/20 text-white transition-colors duration-200 hover:bg-gray-500/10"
          onClick={handleNextClick}
        >
          Next
        </button>
      </div>
    </div>
  );
};
