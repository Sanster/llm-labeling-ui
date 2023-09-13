import { IconCheck, IconKey, IconX } from '@tabler/icons-react';
import { useContext } from 'react';
import { FC, KeyboardEvent, useEffect, useRef, useState } from 'react';

import { useTranslation } from 'next-i18next';

import HomeContext from '@/utils/home.context';

interface Props {
  page: number;
  totalConversations: number;
  totalPages: number;
  onPageChange: (page: number) => void;
}

export const PageInput: FC<Props> = ({
  page,
  totalConversations,
  totalPages,
  onPageChange,
}) => {
  const [isChanging, setIsChanging] = useState(false);
  const [newPage, setNewPage] = useState(page);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleEnterDown = (e: KeyboardEvent<HTMLDivElement>) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      handleUpdateKey(newPage);
    }
  };

  const handleUpdateKey = (newPage: number) => {
    onPageChange(newPage - 1);
    setNewPage(newPage);
    setIsChanging(false);
  };

  useEffect(() => {
    if (isChanging) {
      inputRef.current?.focus();
    }
  }, [isChanging]);

  return isChanging ? (
    <div className="duration:200 flex w-full cursor-pointer items-center rounded-md py-1 px-3 transition-colors hover:bg-gray-500/10">
      <input
        ref={inputRef}
        className="[appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none w-[30px] h-[20px] flex-1 overflow-hidden overflow-ellipsis border-b border-neutral-400 bg-transparent pr-1 text-[12.5px] leading-3 text-left text-white outline-none focus:border-neutral-100"
        type="number"
        value={newPage}
        onChange={(e) => setNewPage(parseInt(e.target.value, 10))}
        onKeyDown={handleEnterDown}
      />

      <div className="flex w-[40px]">
        <IconCheck
          className="ml-auto min-w-[20px] text-neutral-400 hover:text-neutral-100"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            handleUpdateKey(newPage);
          }}
        />

        <IconX
          className="ml-auto min-w-[20px] text-neutral-400 hover:text-neutral-100"
          size={18}
          onClick={(e) => {
            e.stopPropagation();
            setIsChanging(false);
            setNewPage(page);
          }}
        />
      </div>
    </div>
  ) : (
    <button
      className="ml-2 cursor-pointer hover:opacity-50"
      onClick={() => setIsChanging(true)}
    >
      {totalPages === 0 ? 0 : `${page} / ${totalPages} (${totalConversations})`}
    </button>
  );
};

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
    homeDispatch({ field: 'selectedConversationPageIndex', value: 0 });
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
    homeDispatch({ field: 'selectedConversationPageIndex', value: 0 });
  };

  const handleChangePage = (page: number) => {
    if (page > totalPages - 1) {
      page = totalPages - 1;
    }
    if (page < 0) {
      page = 0;
    }
    homeDispatch({
      field: 'page',
      value: page,
    });
    homeDispatch({ field: 'selectedConversationPageIndex', value: 0 });
  };

  return (
    <div className="flex w-full flex-col gap-1">
      <div className="flex flex-row w-full items-center justify-between">
        <button
          className="text-sidebar py-1 w-[30px] flex-shrink-0 cursor-pointer select-none items-center rounded-md border border-white/20 text-white transition-colors duration-200 hover:bg-gray-500/10"
          onClick={handlePrevClick}
        >
          {'<'}
        </button>
        <PageInput
          page={page + 1}
          totalPages={totalPages}
          totalConversations={totalConversations}
          onPageChange={handleChangePage}
        />
        <button
          className="text-sidebar py-1 w-[30px] flex-shrink-0 cursor-pointer select-none items-center rounded-md border border-white/20 text-white transition-colors duration-200 hover:bg-gray-500/10"
          onClick={handleNextClick}
        >
          {'>'}
        </button>
      </div>
    </div>
  );
};
